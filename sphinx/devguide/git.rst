.. _git-interface:

************************
Version control with Git
************************


Very short and practical oriented documentation on using Git for Vortex.

=========
Git setup
=========

Init
====

At the very begining, you should configure your own profile :

.. code-block:: console

  % git config --global user.name "Eric Sevault"
  % git config --global user.email eric.sevault@meteo.fr
  % git config --list
  user.email=eric.sevault@meteo.fr
  user.name=Eric Sevault

and basic definitions :

.. code-block:: console

  % git config --global core.editor vim
  % git config --global merge.tool meld
  % git config --list
  user.email=eric.sevault@meteo.fr
  user.name=Eric Sevault
  core.editor=kate
  merge.tool=meld

You can check a specific value with these names :


.. code-block:: console

  % git config user.name
  Eric Sevault


Files to ignore
===============

In order to avoid unexpected staging of temporary files,
you should intert in the :file:`$HOME/.gitignore` the folowing lines :

.. code-block:: console

  % cat $HOME/.gitignore
  *.pyc
  *.log
  *~
  *.pid

First access to depot
=====================

Let assume you want to work in a traditional directory :file:`git-dev` :

.. code-block:: console

  % mkdir -p $HOME/git-dev
  % cd $HOME/git-dev
  % git clone mrpm631@yuki:/mf/dp/marp/marp001/git-dev/vortex
  % ls -l
  total 4
  drwxr-xr-x 4 esevault gmap 4096 2012-09-26 17:25 vortex/

You have now a full copy of the source history, with a view on the last master release.

======
Basics
======

Status
======

The main tool you use to determine which files are in which state
is the :command:`git status` command.
If you run this command directly after a clone, you should see something like this :

.. code-block:: console

  % git status
  # On branch master
  nothing to commit (working directory clean)

Staging or adding a file
========================

After a modification, you may want to record that
this file should join -- in that stage -- the next commit :

.. code-block:: console

  % vi vortex/data/containers.py
  % git add vortex/data/containers.py

This is also true for new files :

.. code-block:: console

  % cd src/sandbox/data
  % vi newclass.py
  % git add newclass.py
  % git status
  # On branch master
  # Changes to be committed:
  #   (use "git reset HEAD <file>..." to unstage)
  #
  #	new file:   newclass.py
  #

One can see that Git provides a information for unstagging a file
(either a new one or an updated one) :

.. code-block:: console

  % git reset HEAD newclass.py

The file is now only "locally modified". If you want also to "unmodifed" it or any other
modified file in the current working directory and therefore retrieve
the last committed state of the art for this file, just do :

.. code-block:: console

  % git checkout -- mymodifiedfile.py


Removing a file
===============

This is equivalent to removing the file from the staged area before committing :

.. code-block:: console

  % cd src/sandbox/data
  % git rm newclass.py
  rm 'src/sandbox/data/newclass.py'
  % git status
  # On branch master
  # Your branch is ahead of 'origin/master' by 1 commit.
  #
  # Changes to be committed:
  #   (use "git reset HEAD <file>..." to unstage)
  #
  #	deleted:    newclass.py
  #

Moving a file
=============

The :command:`git mv` command is a shortcut to remove and add sequence,
in order to produce a rename of a file or directory :

.. code-block:: console

  % git mv resources.py foo.py
  % git status
  # On branch master
  # Your branch is ahead of 'origin/master' by 1 commit.
  #
  # Changes to be committed:
  #   (use "git reset HEAD <file>..." to unstage)
  #
  #	renamed:    resources.py -> foo.py
  #


Committing
==========

Now that your staging area is set up the way you want it,
you can commit your changes. Anything that is still unstaged
(any files you have created or modified that you haven't run :command:`git add`
on since you edited them) won't go into this commit.
They will stay as modified files on your disk.
In this case, the last time you ran :command:`git status`,
you saw that everything was staged, so you're ready to commit your changes.
The simplest way to commit is to type :

.. code-block:: console

  % git commit

You may amend this commit if you add forgotten a file for exemple,
or to change the comment. In that case, the new staging area will be committed
in place of the previous one :

.. code-block:: console

  % git commit --amend


Commit history
==============

The most basic way to retrieve information, is the simple :command:`git log` command,
which is paged :

.. code-block:: console

  % git log
  commit 8a6a553e91977c557a31a65e164f2c199e57afb2
  Author: Eric Sevault <eric.sevault@meteo.fr>
  Date:   Thu Sep 27 14:12:03 2012 +0200

      An other try

  commit 4bf4f199458dd9c7f20aab22ed64a534674d92cf
  Author: Eric Sevault <eric.sevault@meteo.fr>
  Date:   Thu Sep 27 14:00:24 2012 +0200

      adding a newclass

  commit 4df976f902d9c57485aad9d84716a5f2decfa171
  Author: GCO Equipe <gco@meteo.fr>
  Date:   Wed Sep 12 09:28:22 2012 +0000

      Version 0.5.4

With some statistics :

.. code-block:: console

  % git log --stat

Limit history depth :

.. code-block:: console

  % git log --since=3.days



