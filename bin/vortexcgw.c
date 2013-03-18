#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <errno.h>

#define MAX_CMD_LINE 256

int main ( int argc, char **argv ) {

    char gwcmd[MAX_CMD_LINE] = "";
    int current_uid = getuid();
    int ierr = 0;

    if ( argc < 3 ) {
         fprintf(stderr, "Usage: vortexgwc source target\n");
         exit(1);
    }

    if ( ierr = setgid( (gid_t) 3850 ) ) {
         fprintf(stderr, "Could not set gid [%d] (%d, %d)\n", errno, EAGAIN, EPERM);
         exit(1);
    }

    if ( ierr = setuid( (uid_t) 23299 ) ) {
         fprintf(stderr, "Could not set euid [%d] (%d, %d)\n", errno, EAGAIN, EPERM);
         exit(1);
    }

    fprintf(stderr, "Gateway root uid: %d %d\n", current_uid, geteuid());
    
    sprintf(gwcmd, "/home_nfs/mastergroup/masteruser/dev/setuid/gwln.py %s %s", argv[1], argv[2]);
    fprintf(stderr, "Gateway root cmd: %s\n", gwcmd);

    execl("/home_nfs/mastergroup/masteruser/dev/setuid/gwln.py", "gwln.py", argv[1], argv[2], (char *) NULL);

    setuid(current_uid);

    return 0;
}

