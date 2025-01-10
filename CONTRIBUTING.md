This contribution guide was adapted from _The Turing Way_'s contribution guide. See [Contributing to _The Turing Way_](https://github.com/the-turing-way/the-turing-way/blob/main/CONTRIBUTING.md).

## Table of contents

- [Get in touch](#get-in-touch)
- [Setting up VORTEX for development](#setting-up-vortex-for-development)
- [Contributing using GitHub](#contributing-through-github)
  - [Writing in Markdown](#writing-in-markdown)
  - [Where to start: issues](#where-to-start-issues)
  - [Making a change with a merge request](#making-a-change-with-a-merge-request)
- [Continuous integration checks](#continuous-integration-checks)

## Get in touch

- GitHub [issues](https://github.com/UMR-CNRM/vortex/issues) and [pull requests](https://github.com/UMR-CNRM/vortex/pulls)
  - Join a discussion, collaborate on an ongoing task and exchange your thoughts with others.
  - Can't find your idea being discussed anywhere?
    [Open a new issue](https://github.com/UMR-CNRM/vortex/issues/new)! (See our [Where to start: issues](#where-to-start-issues) section below.)
- Support mailing list
  - You can email support queries at `vortex-support@meteo.fr`.
    Please, however, favor GitHub issues over this mailing list. They allow other users and developers to contribute to the solution and to benefit from it.

## Setting up *vortex* for development

Start with cloning the *vortex* repository, for example:

```
git clone https://github.com/UMR-CNRM/vortex
```

It is highly recommended that you install *vortex* in a Python virtual environment, so as to isolate it and its dependencies from Python libraries that are already installed on your system, or that you will install in the future.

After creating and activating a [Python virtual environment](https://docs.python.org/3/library/venv.html), install *vortex* in editable mode:

```
pip install --editable .[docs]
```

The `--editable` option ensures that you won't have to reinstall *vortex* everytime you make a change to it, see [Development Mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html).

The `[docs]` suffix indicates that you want `pip` to install the optional set of dependencies required to build the documentation website locally.
Then add both directories `src` and `site` to the `PYTHONPATH` environment variable.

## Contributing using GitHub

[Git](git-scm.com) is a really useful tool for version control.
[GitHub](https://github.com/about) is web-based software that sit on top of Git and facilitates collaborative and distributed working.

It can be daunting to start using Git and GitHub if you haven't worked with them in the past, but the *vortex* team is here to help you figure out any of the jargon or confusing instructions you encounter.

In order to contribute via GitHub, you'll need to [set up an account](https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github) and sign in.

### Writing in Markdown

Most of the writing that you will do will be in [Markdown](https://en.wikipedia.org/wiki/Markdown).
You can think of Markdown as a few little symbols around your text that will allow GitHub to render the text with a little bit of formatting.
For example, you could write words as **bold** (`**bold**`), or in _italics_ (`_italics_`), or as a [link][rick-roll] (`[link](https://youtu.be/dQw4w9WgXcQ)`) to another webpage.

You'll find a useful guide outline the basic syntax of Markdown at [markdownguide.org](https://www.markdownguide.org/basic-syntax).

When writing in Markdown, please [start each new sentence on a new line](https://book.the-turing-way.org/community-handbook/style.html#write-each-sentence-in-a-new-line-line-breaks).
Having each sentence on a new line will make no difference to how the text is displayed, there will still be paragraphs, but it makes the [diffs produced during the pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-comparing-branches-in-pull-requests) review easier to read! :sparkles:

### Where to start: issues

Before you open a new issue, please check if any of our [open issues](https://github.com/UMR-CNRM/vortex/issues) cover your idea already.

Issues don't have to be technical: they could be about documentation you find unclear or missing, ideas for new features, or suggestions on how to make a part of *vortex* better.

### Making a change with a merge request

We appreciate all contributions to *vortex*, whether they include changes to code itself or the documentation.

The following steps are a guide to help you contribute in a way that will be easy for everyone to review and merge your work into the project.

### 1. Comment on an [existing issue](https://github.com/UMR-CNRM/vortex/issues) or open a new issue referencing your contribution

This allows other members of *vortex* team to confirm that you aren't overlapping with work that's currently underway and that everyone is on the same page with the goal of the work you're going to carry out.

[This blog](https://www.igvita.com/2011/12/19/dont-push-your-pull-requests/) is a nice explanation of why putting this work in upfront is so useful to everyone involved.

### 2. Make the changes you've discussed

Start with creating a new Git branch from where you will make your changes.
Please start this branch from a recent copy of the `main` branch.
You can update your local copy with `git pull`

```shell
git switch main
git pull origin main
```

Then create and switch to your new branch with `git switch`:
```
$ git switch -c main
```

Are you new to Git and GitHub or just want a detailed guide on getting started with version control? Check out the [Version Control chapter](https://book.the-turing-way.org/version_control/version_control.html) in _The Turing Way_ Book!

Try to keep the changes focused.
If you submit a large amount of work all in one go it will be much more work for whoever is reviewing your merge request.

While making your changes, commit often and write detailed commit messages.
[This blog](https://chris.beams.io/posts/git-commit/) explains how to write a good Git commit message and why it matters.
It is also perfectly fine to have a lot of commits - *including ones that break code*.
It is often difficult to assess or frequently you should push your changes to the GitHub repository. 
Think of pushing changes as sharing your work with other developers involved in the project. 
Pushing everytime you commit a change is uncessery, but waiting too long before making your work -- even incomplete -- available will make it very difficult for anyone to follow your progress.
Worse, it will make it much harder for maintainers to review your contribution.

### 4. Submit a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)

We encourage you to open a merge request as early in your contributing process as possible.
This allows everyone to see what is currently being worked on and provides you, the contributor, feedback in real-time from the community.

The pull request description section is **very important**.
A good description can make the contribution process dramatically faster, but a short, vague description will almost certainly slow it down.
A a rule of thumb, a pull request description should, at the minimum, feature the following information:

- An accurate description of the problem you're trying to fix in the merge request, with reference(s) to any related issue(s).
- A list of changes proposed in the merge request.

In addition, it is often beneficial to include a description of what the reviewer(s) should concentrate their feedback on.

If you have opened the merge request early and know that its contents are not ready for review or to be merged, [convert it to a draft](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request#converting-a-pull-request-to-a-draft).
When you are happy with it and are happy for it to be merged into the main repository, [mark it as ready for review](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request#marking-a-pull-request-as-ready-for-review).

One or more of *vortex* team members will then review your changes to confirm that they can be merged into the main repository.
A [review](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews) will probably consist of a few questions to help clarify the work you've done.
Keep an eye on your [GitHub notifications](https://docs.github.com/en/account-and-profile/managing-subscriptions-and-notifications-on-github/setting-up-notifications/configuring-notifications) and be prepared to join in that conversation.

## Contributing from a fork

This is an alternative to creating and pushing your own branch to the *vortex* repository.
This is the only way to contribute to the project is your GitHub account does not yet have persmission to push a branch to the *vortex* repository.

The *vortex* repository GitHub page offers [a fork button](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#forking-a-repository) that can be used to create a personal copy of the project, under your personal GitHub account.
This copy, commonly known as _fork_ is a completely separate repository from the original one.

You can contribute changes made in a fork back to the upstream repository.
However, two pieces of advice:

- Make sure to [keep your fork up to date](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork) with the main repository, otherwise, you can end up with lots of dreaded [merge conflicts](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts/about-merge-conflicts).
- Read [https://hynek.me/articles/pull-requests-branch/](https://hynek.me/articles/pull-requests-branch/).

