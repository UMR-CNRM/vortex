import io
import os
import sys
import tarfile


_GGET_MANTRA = 'This is a fake gget file.'


def fakefile01():
    with open('fakefile.01', 'w') as fhtmp:
        fhtmp.write(_GGET_MANTRA)


def fakedir01(dirname='fakedir.01'):
    os.mkdir(dirname)
    os.mkdir(os.path.join(dirname, 'subdir'))
    for f in ('file1', 'file2', 'file3'):
        with open(os.path.join(dirname, f), 'w') as fhtmp:
            fhtmp.write(_GGET_MANTRA)
    for f in ('file4', 'file5'):
        os.symlink('./file1', os.path.join(dirname, f))
    os.symlink('../file1', os.path.join(dirname, 'subdir', f))


def fakedir02():
    fakedir01('fakedir.02')


def fakedir01_ext():
    with open('file4', 'w') as fhtmp:
        fhtmp.write(_GGET_MANTRA)


def fakedir01_ext2():
    os.symlink('file4', 'file5')


def fakedir01_ext3():
    fakedir01_ext()
    os.symlink('file4', 'file6')


def fakearch01():
    tfobj = tarfile.open(name='fakearchive.01.tgz', mode='w:gz')
    try:
        adir = tarfile.TarInfo('subdir')
        adir.type = tarfile.DIRTYPE
        tfobj.addfile(adir)
        for f in ('file1', 'file2', 'file3'):
            afile = tarfile.TarInfo(f)
            afile.size = len(_GGET_MANTRA)
            afile_fh = io.BytesIO()
            afile_fh.write(_GGET_MANTRA.encode())
            afile_fh.seek(0)
            tfobj.addfile(afile, afile_fh)
        for f in ('file4', 'file5'):
            alink = tarfile.TarInfo(f)
            alink.type = tarfile.SYMTYPE
            alink.linkname = './file1'
            tfobj.addfile(alink)
    finally:
        tfobj.close()


_AUTHORIZED = {('fakefile.01', ): fakefile01,
               ('fakedir.01', ): fakedir01,
               ('fakedir.02', ): fakedir02,
               ('-extract', '-subdir=no', 'fakedir.01', 'file4'): fakedir01_ext,
               ('-extract', '-subdir=no', 'fakedir.01', 'file5'): fakedir01_ext2,
               ('-extract', '-subdir=no', 'fakedir.01', 'file6'): fakedir01_ext3,
               ('fakearchive.01.tgz', ): fakearch01}


if __name__ == "__main__":
    todo = sys.argv[1:]
    assert todo[0] == '-host'
    todo = todo[2:]
    _AUTHORIZED[tuple(todo)]()
