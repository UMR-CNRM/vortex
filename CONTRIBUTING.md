This contribution guide was adapted from _The Turing Way_'s contribution guide. See [Contributing to _The Turing Way_](https://github.com/the-turing-way/the-turing-way/blob/main/CONTRIBUTING.md).

## Table of contents

- [Get in touch](#get-in-touch)
- [Setting up VORTEX for development](#setting-up-vortex-for-development)
- [Contributing through GitLab](#contributing-through-gitlab)
  - [Writing in Markdown](#writing-in-markdown)
  - [Where to start: issues](#where-to-start-issues)
  - [Making a change with a merge request](#making-a-change-with-a-merge-request)
- [Continuous integration checks](#continuous-integration-checks)

## Get in touch

- GitLab [issues](https://git.meteo.fr/cnrm-gmap/vortex/-/issues) and [merge requests](https://git.meteo.fr/cnrm-gmap/vortex/-/merge_requests)
  - Join a discussion, collaborate on an ongoing task and exchange your thoughts with others.
  - Can't find your idea being discussed anywhere?
    [Open a new issue](https://git.meteo.fr/cnrm-gmap/vortex/-/issues/new)! (See our [Where to start: issues](#where-to-start-issues) section below.)
- [rocket.chat channel](https://chat.meteo.fr/channel/vortex)
  - For structured discussion and sustained engagement with the community members.
  - We will also provide notifications on upcoming events and share useful resources on the chat.
- Support mailing list
  - You can email support queries at `vortex-support@meteo.fr`.
    Please, however, favor GitLab issues over this mailing list. It
    allows other users and developers to contribute to the solution
    and to benefit from it.

## Setting up VORTEX for development

It all starts with

```
git clone https://git.meteo.fr/cnrm-gmap/vortex.git
```

which downloads the project into a new `vortex` directory within your current directory.

Then add both directories `src` and `site` to the `PYTHONPATH` environment variable.

```shell
VORTEX_BASE_DIR=/absolute/path/to/vortex
export PYTHONPATH=$VORTEX_BASE_DIR/src:$VORTEX_BASE_DIR/site
```

Finally, install a few utility Python packages, later required to run
[automated checks](#Continuous-Integration-(CI)-checks).
It is recommended that you install in a dedicated Python virtual environemnt:

```shell
$ python3 -m venv vortex-dev
$ source vortex-dev/bin/activate
(vortex-dev)$ pip install pytest pyyaml pycodestyle pydocstyle astroid
```

You can use the `deactivate` command to deactivate the virtual environment.

## Contributing through GitLab

[Git](git-scm.com) is a really useful tool for version control.
[GitLab](https://about.gitlab.com) sits on top of Git and facilitates collaborative and distributed working.
GitLab is web-browser based software that can be either used from GitLab's (the company) servers or deployed independently by institutions. 
At Météo-France, the DSI/MOD team administrates the [git.meteo.fr](git.meteo.fr) GitLab instance. See [GitLab - Gestionnaire de code source](http://confluence.meteo.fr/display/MOT/GitLab+-+Gestionnaire+de+code+source) for more information about GitLab at Météo-France.

We know that it can be daunting to start using Git and GitLab if you haven't worked with them in the past, but VORTEX maintainers are here to help you figure out any of th jargon or confusing instructions you encounter! :heart:

In order to contribute via GitLab, you'll need to set up an account and sign in.  If you you have a Météo-France LDAP account, use it!
Your GitLab account will automatically created upon your first login.

### Writing in Markdown

Most of the writing that you'll do will be in [Markdown](https://en.wikipedia.org/wiki/Markdown).
You can think of Markdown as a few little symbols around your text that will allow GitHub to render the text with a little bit of formatting.
For example, you could write words as **bold** (`**bold**`), or in _italics_ (`_italics_`), or as a [link][rick-roll] (`[link](https://youtu.be/dQw4w9WgXcQ)`) to another webpage.

You'll find a useful guide outline the basic syntax of Markdown at [markdownguide.org](https://www.markdownguide.org/basic-syntax).

When writing in Markdown, please [start each new sentence on a new line](https://book.the-turing-way.org/community-handbook/style.html#write-each-sentence-in-a-new-line-line-breaks).
Having each sentence on a new line will make no difference to how the text is displayed, there will still be paragraphs, but it makes the [diffs produced during the merge request](https://docs.gitlab.com/ee/user/project/merge_requests/changes.html) review easier to read! :sparkles:

### Where to start: issues

Before you open a new issue, please check if any of our [open issues](https://git.meteo.fr/cnrm-gmap/vortex/-/issues) cover your idea already.

Issues don't have to be technical: they could be about documentation you find unclear or simply missing, ideas for new features or suggestions on how to make a part of VORTEX better.

### Making a change with a merge request

We appreciate all contributions to VORTEX, whether as changes to code or documentation.

All project management, conversations and questions related to the VORTEX project happens here in [VORTEX repository](https://git.meteo.fr/cnrm-gmap/vortex).
This is also where you can contribute directly to writing or editing code or documentation.

The following steps are a guide to help you contribute in a way that will be easy for everyone to review and accept with ease.

### 1. Comment on an [existing issue](https://git.meteo.fr/cnrm-gmap/vortex/-/issues) or open a new issue referencing your addition

This allows other members of VORTEX team to confirm that you aren't overlapping with work that's currently underway and that everyone is on the same page with the goal of the work you're going to carry out.

[This blog](https://www.igvita.com/2011/12/19/dont-push-your-pull-requests/) is a nice explanation of why putting this work in upfront is so useful to everyone involved.

### 2. Make the changes you've discussed

Start with creating a new Git branch from where you will make your changes.
Please start this branch from a recent copy of the `olive-dev` branch.
You can update your local copy with `git pull`

```shell
git switch olive-dev
git pull origin olive-dev
```

Then create and switch to your new branch with `git switch`:
```
$ git switch -c my-new-branch
```

Are you new to Git and GitLab or just want a detailed guide on getting started with version control? Check out the [Version Control chapter](https://book.the-turing-way.org/version_control/version_control.html) in _The Turing Way_ Book!

Try to keep the changes focused.
If you submit a large amount of work all in one go it will be much more work for whoever is reviewing your merge request.

While making your changes, commit often and write detailed commit messages.
[This blog](https://chris.beams.io/posts/git-commit/) explains how to write a good Git commit message and why it matters.
It is also perfectly fine to have a lot of commits - *including ones that break code*.
A good rule of thumb is to push up to GitLab when you _do_ have passing tests then the continuous integration (CI) has a good chance of passing everything.

### 3. Before your push

Before pushing changes, it is recommanded to run automatic checks locally on your developement machine. From the root of the repository, run

- `make check`: runs a fairly quick suite of tests (~25s)
- `make style`: checks PEP8 formatting, comments layout, unused
  variables and imports...
- `cd sphinx && make miss-check`: checks for missing documentation.

This assumes various required utility packages such as `pytest` or `atroid` are installed in the current Python environemnt.
See [Setting up VORTEX for developement](#Setting-up-VORTEX-for-developement).

As a bonus, you can run a longer suite of tests by running `make tests` from the root of the repository.

These checks will be run against your changes by the GitLab server _anyway_.
But by running them locally before pushing, you will save yourself numerous, time consuming back and forth between your GitLab merge request and your local developement environment.

### 4. Submit a [merge request](https://docs.gitlab.com/ee/user/project/merge_requests/)

We encourage you to open a merge request as early in your contributing process as possible.
This allows everyone to see what is currently being worked on.
It also provides you, the contributor, feedback in real-time from both the community and the continuous integration as you make commits. This will help prevent stuff from breakin.

When you are ready to submit a merge request, you will automatically see the [Merge Request Template](https://git.meteo.fr/cnrm-gmap/vortex/-/blob/olive-dev/.gitlab/merge_request_templates/default.md) contents in the merge request body.
It asks you to:

- Describe the problem you're trying to fix in the merge request, reference any related issue and use fixes/close to automatically close them, if pertinent.
- List of changes proposed in the merge request.
- Describe what the reviewer should concentrate their feedback on.

By filling out sections of the merge request template with as much detail as possible, you will make it really easy for someone to review your contribution!

If you have opened the merge request early and know that its contents are not ready for review or to be merged, add "[WIP]" at the start of the merge request title, which stands for "Work in Progress".
When you are happy with it and are happy for it to be merged into the main repository, change the "[WIP]" in the title of the merge request to "[Ready for review]".

A member of VORTEX team will then review your changes to confirm that they can be merged into the main repository.
A [review](https://docs.gitlab.com/ee/user/project/merge_requests/reviews/) will probably consist of a few questions to help clarify the work you've done.
Keep an eye on your GitHub notifications and be prepared to join in that conversation.

You can also submit merge requests to other contributors' branches!
Do you see an [open merge request](https://git.meteo.fr/cnrm-gmap/vortex/-/merge_requests) that you find interesting and want to contribute to?
Simply make your edits on their files and open a merge request to their branch.

## Continuous integration checks

Each time new commits are pushed to a remote branch for which a merge request is opened, automatic checks are performed.

Roughly, these merge request checks are about:
- Checking documentation.
- Checking code style.
- Running a suite of automated tests.

The sequence of checks is commonly referred to as a _merge request pipeline_.
A contribution will be merged _only_ if the associated merge request pipeline passed.
If it fails, you will be asked to make and push the necessary change for the pipeline to pass, before your changes are merged in the target branch.

What happens if the continuous integration (CI) fails (for example, if the merge request notifies you that "Some checks were not successful")?
The CI could fail for a number of reasons.
At the bottom of the merge request, where it says whether your build passed or failed, you can click “Details” next to the test, which takes you to a CI run log site.
If you have the write access to the repo, you can view the log or rerun the checks by clicking the “Restart build” button in the top right.
You can learn more about CI in the [Continuous Integration chapter](https://book.the-turing-way.org/reproducible-research/ci.html) of _The Turing Way_.

## Contributing from a fork

This is an alternative to creating and pushing your own branch to the VORTEX repository.

The VORTEX repository GitLab page offers a fork button that can be used to create a persnal copy of the project, under your personal GitLab account.
This copy, commonly known as _fork_ is a completely separate repository from the original one.

You can contribute changes made in a fork back to the upstream repository, see [Merge changes back upstream](https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html#merge-changes-back-upstream).

You can choose to work with a fork instead of pushing commits straight to the VORTEX repository, if you so wish.

However, two pieces of advice:

- Make sure to [keep your fork up to date](https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html#update-your-fork) with the main repository, otherwise, you can end up with lots of dreaded [merge conflicts](https://docs.gitlab.com/ee/user/project/merge_requests/conflicts.html).
- Read [https://hynek.me/articles/pull-requests-branch/](https://hynek.me/articles/pull-requests-branch/).

