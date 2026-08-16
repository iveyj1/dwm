/* Send a command to dwm and place its next window on a chosen tag. */
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/Xatom.h>
#include <X11/Xlib.h>

int
main(int argc, char **argv)
{
	Atom atom;
	Display *dpy;
	Window root;
	char *data, *p, *end;
	long tag;
	size_t len;
	int i, screen;

	if (argc < 3) {
		fprintf(stderr, "usage: dwm-spawn tag command [argument ...]\n");
		return 2;
	}
	errno = 0;
	tag = strtol(argv[1], &end, 10);
	if (errno || *end || tag < 1 || tag > 31) {
		fprintf(stderr, "dwm-spawn: tag must be a number from 1 to 31\n");
		return 2;
	}
	len = strlen(argv[1]) + 1;
	for (i = 2; i < argc; i++) {
		if (SIZE_MAX - len <= strlen(argv[i])) {
			fprintf(stderr, "dwm-spawn: command is too long\n");
			return 1;
		}
		len += strlen(argv[i]) + 1;
	}
	if (len > INT_MAX) {
		fprintf(stderr, "dwm-spawn: command is too long\n");
		return 1;
	}
	if (!(data = malloc(len))) {
		perror("dwm-spawn: malloc");
		return 1;
	}
	p = data;
	memcpy(p, argv[1], strlen(argv[1]) + 1);
	p += strlen(argv[1]) + 1;
	for (i = 2; i < argc; i++) {
		memcpy(p, argv[i], strlen(argv[i]) + 1);
		p += strlen(argv[i]) + 1;
	}
	if (!(dpy = XOpenDisplay(NULL))) {
		fprintf(stderr, "dwm-spawn: cannot open display\n");
		free(data);
		return 1;
	}
	screen = DefaultScreen(dpy);
	root = RootWindow(dpy, screen);
	atom = XInternAtom(dpy, "_DWM_SPAWN", False);
	XChangeProperty(dpy, root, atom, XA_STRING, 8, PropModeReplace,
	                (unsigned char *)data, len);
	XSync(dpy, False);
	XCloseDisplay(dpy);
	free(data);
	return 0;
}
