"""Linux wpa_supplicant control client and network transactions."""
import os
import re
import socket
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path


class Failure(Exception):
    pass


class Control:
    def __init__(self, directory, iface):
        self.stack = ExitStack()
        try:
            tmp = self.stack.enter_context(tempfile.TemporaryDirectory(prefix='wsup-'))
            def endpoint(name):
                s = self.stack.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM))
                s.bind(os.path.join(tmp, name))
                s.connect(str(Path(directory) / iface))
                s.settimeout(2)
                return s
            self.cmd = endpoint('cmd')
            self.events = endpoint('events')
            self.events.send(b'ATTACH')
            if self.events.recv(1024).strip() != b'OK':
                raise Failure('ATTACH failed')
            self.events.setblocking(False)
        except BaseException:
            self.stack.close()
            raise

    def ask(self, command):
        self.cmd.send(command.encode('ascii'))
        try:
            result = self.cmd.recv(262144).decode('ascii', 'backslashreplace').rstrip('\n')
        except TimeoutError:
            self.cmd.close()  # late responses cannot be paired with subsequent commands
            raise Failure('Control request timed out; restart client') from None
        if result.startswith(('FAIL', 'UNKNOWN COMMAND')):
            raise Failure(command.split()[0] + ' failed')
        return result

    def event(self):
        try:
            return self.events.recv(8192).decode('ascii', 'replace')
        except BlockingIOError:
            return ''


def unescape(s):
    return re.sub(rb'\\(?:x([0-9a-fA-F]{2})|([\\"nret]))', lambda m: bytes([int(m[1], 16)]) if m[1] else {b'n': b'\n', b'r': b'\r', b'e': b'\x1b', b't': b'\t'}.get(m[2], m[2]), s.encode('ascii'))


def display(raw):
    return ''.join(chr(b) if 32 <= b < 127 and b != 92 else '\\x%02x' % b for b in raw)


def mode(flags):
    tags = re.findall(r'\[([^]]+)\]', flags)
    if 'ESS' not in tags:
        return 'unsupported'
    if any(re.fullmatch(r'(?:WPA2|RSN)-PSK(?:\+SAE)?-(?:CCMP|TKIP)(?:\+(?:CCMP|TKIP))*', t) for t in tags):
        return 'WPA2'
    return 'open' if all(t in ('ESS', 'WPS', 'UTF-8') for t in tags) else 'unsupported'


def access_points(text):
    aps = []
    for line in text.split('\n')[1:]:
        fields = line.split('\t', 4)
        if len(fields) == 5 and fields[1].isdigit() and re.fullmatch('-?[0-9]+', fields[2]):
            key = unescape(fields[4]), mode(fields[3])
            aps.append((key, fields[0].lower(), int(fields[1]), int(fields[2])))
    return sorted(aps, key=lambda ap: -ap[3])


def channel(freq):
    if freq == 2484:
        return '2.4 GHz', 14
    if 2412 <= freq <= 2472 and (freq-2407)%5 == 0:
        return '2.4 GHz', (freq-2407)//5
    if 5005 <= freq <= 5895 and freq%5 == 0:
        return '5 GHz', (freq-5000)//5
    if freq == 5935:
        return '6 GHz', 2
    if 5955 <= freq <= 7115 and (freq-5950)%5 == 0:
        return '6 GHz', (freq-5950)//5
    return '?', None


def group_aps(aps):
    rows = {}
    for key, _, _, db in aps:
        if key[0] and any(key[0]):
            rows[key] = max(rows.get(key, db), db)
    return sorted(rows.items(), key=lambda row: -row[1])


def scan(text):
    return group_aps(access_points(text))


def credential(value):
    if re.fullmatch('[a-fA-F0-9]{64}', value):
        return value
    if not re.fullmatch('[ -~]{8,63}', value):
        raise Failure('Use 8–63 printable ASCII characters or 64 hex digits')
    return '"' + value + '"'  # SET_NETWORK uses the first and last quotes as delimiters


class Manager:
    def __init__(self, ctl):
        self.c = ctl
        self.q = ctl.ask
        self.temp = set()

    def status(self):
        return dict(line.split('=', 1) for line in self.q('STATUS').splitlines() if '=' in line)

    def profiles(self):
        profiles = {}
        for line in self.q('LIST_NETWORKS').split('\n')[1:]:
            i, ssid, _, flags = line.split('\t')
            if not i.isdecimal():
                raise Failure('Invalid network id')
            try:
                tag = self.q('GET_NETWORK '+i+' id_str')
            except Failure as e:
                if str(e) != 'GET_NETWORK failed':
                    raise
                tag = ''
            if tag == '"wsup-tui-temporary-v1"':
                self.temp.add(i)
            else:
                self.temp.discard(i)
            km = self.q('GET_NETWORK '+i+' key_mgmt').split()
            security = 'unsupported'
            if 'WPA-PSK' in km and 'RSN' in self.q('GET_NETWORK '+i+' proto').split():
                security = 'WPA2'
            if km == ['NONE']:
                for j in range(4):
                    try:
                        self.q(f'GET_NETWORK {i} wep_key{j}')
                        break
                    except Failure as e:
                        if str(e) != 'GET_NETWORK failed':
                            raise
                else:
                    security = 'open'
            profiles[i] = ((unescape(ssid), security), flags)
        self.temp.intersection_update(profiles)
        return profiles

    def save(self, i, prefer, profiles):
        if self.temp - {i}:
            raise Failure('Save refused: unrelated temporary profile exists')
        old = None
        if prefer:
            values = {n: int(self.q('GET_NETWORK '+n+' priority')) for n in profiles}
            old = values.get(i, 0)
            priority = max([0] + list(values.values())) + 1
            if priority > 2147483647:
                raise Failure('Priority limit reached')
            self.q(f'SET_NETWORK {i} priority {priority}')
        temporary = i in self.temp
        try:
            if temporary:
                self.q(f'SET_NETWORK {i} id_str "wsup-tui-saved"')
            self.q('SAVE_CONFIG')
        except Failure:
            if temporary:
                self.q(f'SET_NETWORK {i} id_str "wsup-tui-temporary-v1"')
            if old is not None:
                self.q(f'SET_NETWORK {i} priority {old}')
            raise
        self.temp.discard(i)

    def connect(self, key, password, action, cancel, timeout=30):
        profiles = self.profiles()
        enabled = [n for n, (_, f) in profiles.items() if '[DISABLED]' not in f]
        previous = self.status().get('id')
        i = next((n for n, (k, _) in profiles.items() if k == key), None)
        new = i is None
        selected = False
        if key[1] not in ('open', 'WPA2') or not 1 <= len(key[0]) <= 32:
            raise Failure('Unsupported network')
        if new:
            psk = credential(password) if key[1] == 'WPA2' else None
            i = self.q('ADD_NETWORK')
            if not i.isdecimal():
                raise Failure('Invalid ADD_NETWORK response')
            self.temp.add(i)
        try:
            if new:
                self.q(f'SET_NETWORK {i} id_str "wsup-tui-temporary-v1"')
                self.q(f'SET_NETWORK {i} ssid {key[0].hex()}')
                self.q(f'SET_NETWORK {i} key_mgmt ' + ('WPA-PSK' if psk else 'NONE'))
                if psk:
                    self.q(f'SET_NETWORK {i} proto RSN')
                    self.q(f'SET_NETWORK {i} psk {psk}')
            self.q('SELECT_NETWORK '+i)
            selected = True
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if cancel.is_set():
                    raise Failure('Cancelled')
                status = self.status()
                if status.get('id') == i and status.get('wpa_state') == 'COMPLETED':
                    break
                event = self.c.event()
                if 'SSID-TEMP-DISABLED' in event and re.search(r'\bid='+i+r'\b', event):
                    raise Failure('Authentication rejected')
                cancel.wait(.2)
            else:
                raise Failure('Association timed out')
        except BaseException:
            if new:
                self.q('REMOVE_NETWORK '+i)
                self.temp.discard(i)
            if selected:
                if previous in profiles:
                    self.q('SELECT_NETWORK '+previous)
                elif not new and i not in enabled:
                    self.q('DISABLE_NETWORK '+i)
                for n in enabled:
                    self.q('ENABLE_NETWORK '+n)
            raise
        for n in enabled:
            if n != i:
                self.q('ENABLE_NETWORK '+n)
        if action != 'once':
            try:
                self.save(i, action == 'prefer', profiles)
            except Failure as e:
                return 'Connected, not saved: '+str(e)
        if action != 'once':
            return 'Connected and saved' + (' as preferred' if action == 'prefer' else '')
        return 'Connected' + (' (temporary profile in supplicant memory)' if i in self.temp else '')
