How to contribute (for developers)
==================================

We are really happy if you want to propose a new feature or changes in
GATE. Please contact us and share your ideas with us - this is how Gate
was born and how it will keep growing!

Propose a pull request:
-----------------------

1) Fork the opengate repository into your own github.
2) Create a branch for the feature you want to contribute, starting from
   the current opengate master branch.
3) Start implementing your ideas in your newly created branch (locally)
   and keep committing changes as you move forward.
4) Prefer several small commits with clear comments over huge commits
   involving many files and changes.
5) Push changes to your github repo. Also pull changes from the
   upstream/master (opengate’s master branch) regularly to stayed
   synced.
6) When you go to the branch in your repository on github, you will have
   the option to create a Pull Request (PR). Please do that - even if
   you are not done yet. You can mark a pull request as ``draft``.
7) We will then see your branch as PR in the opengate repository and can
   better understand what you are working on, and help you out if
   needed.
8) Ideally, go to the opengate repository and open your own pull
   request. You should see a checkbox below on the right side saying
   “Allow edits and access to secrets by maintainers”. Please tick it.
   In this way, we can directly commit changes into your branch - of
   course we’ll be in touch with you.

More info about `Pull Requests on
github <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests>`__.

Tests and documentation
-----------------------

It is important to make sure that Gate keeps working consistently and
that simulation outcome is reliable as we keep developing the code.
Therefore, we have a large set of tests which are regularly run. If you
propose new features or make changes to the inner workings of Gate,
please create a little test simulation that goes with it. It should be
imlpemented in such a way that it checks whether the feature works as
expected. This might be a check of Geant4 parameters, e.g. if production
cuts are set correctly, or based on simulation outcome, such as a dose
maps or a particle phase space. Best is to look at the folder ``tests``
in the source code.

Your test will also serve other users as example on how the new feature
is used.

There is a set of functions useful for tests in
``opengate/tests/utility.py`` which you can, e.g., import as

.. code:: python

   from opengate.tests import utility

Finally, please write up some lines of documentation, both for the user
and/or the developer.

Code formatting
---------------

We provide a `pre-commit <https://pre-commit.com/>`__ to enforce code
format. In order to use it, you can install it with:

.. code:: bash

   pip install pre-commit
   # then move to the opengate folder and do:
   pre-commit install

Do not worry, if you forget to install it - you/we will see the error
during the automatic testing (Continuous Integration) in Github and can
fix it then through another commit.
