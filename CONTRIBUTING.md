# Contributing

Not1MM is an open-source project and we welcome contributions from the community.

If you'd like to contribute, please fork the repository and make changes as
you'd like. Pull requests are welcome.

Please be kind and run your code thru [black](https://github.com/psf/black)
before submitting: After `pip install black`, run `black not1mm test`.

For additional Karma, also consider running the automated tests:
After `pip install pytest pytest-qt`, run
`PYTHONPATH=$(pwd) pytest test/contests.py`.

Please see [this](https://hynek.me/articles/pull-requests-branch/) page before
you start writing code on your pull request. It will make your life a little
easier.

If accessing a Python dictionary value please use the dictionaries `.get()` function, and provide a sane default value in case the dict key does not exist. So instead of:

```python
name = self.preference["myname"]
```

use:

```python
name = self.preference.get("myname", "OOPS! no name was given, so you get this string")
```

