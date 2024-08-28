# BUR tool

This script aims at automating the process for off-site upload and download of the ENMaaS backup sets, according to the requirements from the
Jira issue [NMAAS-516](https://jira-nam.lmera.ericsson.se/browse/NMAAS-516).

It basically does the following for each option:

1. **Upload**
    1. Reads the parameters from a configuration file and CLI.
    2. Retrieve the list of valid backups from the specified customer or from all customers
    sequentially if no one is defined.
    3. Process the upload for each backup in the list.
    4. Encrypt the data using gpg tool and compress before uploading to offsite.
    5. Deletes any backup sets, other than last 3, from the offsite.

2. **Download**

    1. Accepts the customer name, backup tag or both as input as well as the destination directory.
    2. Lists the available backup sets for a customer.
    3. Extracts and decrypts the backup content after downloading.

# Quickstart

To run the application, you have couple options:

### Manual installation

1. Manually create distribution with backup package.
2. Transfer it to desired location.
3. Unpackage.
4. Run it by calling ```python cli.py <args>```

**Note:** there are external dependencies that must be pre-installed: [gnupg, enum]
You can install them using: ```pip install <package-name>```

### Automated installation using tox (setuptools and wheels) 

1. Go to parent of the backup project (where tox.ini is located)
2. Execute: ```tox -e build```
3. Transfer **enmaas_bur-<version>-py2.py3-none-any.whl** file from **dist** folder to desired location.
4. Execute: ```pip install enmaas_bur-<version>-py2.py3-none-any.whl```
5. Run it by calling ```python -m bur <args>``` or ```bur <args>```

**Note:** More information on **tox** and **.whl** is available down below.

### Expected arguments

To display detailed help message in CLI - just pass ```--usage``` argument.

# For developers

### Prerequisites
**Read and install this as global python packages.**        
The project packages (i.e. gnupg, enum, etc...) should be installed in venv (read about Pipenv and python virtualenvs to understand the difference).

* **Pip** is a package management system used to install and manage software packages written in Python.
    * link: https://pypi.org/project/pip/
    * install: 
        * python2: ```apt install python-pip```
        * python3: ```apth install python3-pip```
* **Pipenv** is a tool that aims to bring the best of all packaging worlds (bundler, composer, npm, cargo, yarn, etc.) to the Python world.
    * link:  https://docs.pipenv.org/
    * install: ```pip install --user pipenv```
* **tox** aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing and release process of Python software.
    * link: https://tox.readthedocs.io/en/latest/
    * install ```pip install tox```
    
### Some other reading
**No need to install these via pip install, as the pipenv will take care of that!**
Just read the docs (in your spare time) to understand why it is important and how it works...

#### Code quality
* **PEP 8** - Style Guide for Python Code
    * link: https://www.python.org/dev/peps/pep-0008/
* **Flake8** - Your Tool For Style Guide Enforcement
    * link: http://flake8.pycqa.org/en/latest/
* **Pylint** is a Python source code analyzer which looks for programming errors, helps enforcing a coding standard and sniffs for some code smells (as defined in Martin Fowler’s Refactoring book).
    * link: https://www.pylint.org/
* **Bandit** - is a tool designed to find common security issues in Python code. 
    * link: https://bandit.readthedocs.io/en/latest/
* **Coverage** is a tool for measuring code coverage of Python programs. It monitors your program, noting which parts of the code have been executed, then analyzes the source to identify code that could have been executed but was not.
    * link: https://coverage.readthedocs.io/en/latest/

### Bootstrap your dev environment

After you've installed all **prerequisites**, now you can create your dev virtual environment with all required dependencies.

Go to parent folder of backup project *(ecm-tools/scripts/python/backup)* and execute: ```pipenv install```        
This command will install all required external dependencies (packages) utilising **Pipfile** and **Pipfile.lock**.

If you want to run tests, linter checks and test coverage from Pipenv shell, you have to install **[dev-packages]** from **Pipfile**.        
Just run: ```pipenv install --dev```  

To uninstall all packages run: ```pipenv uninstall --all```

If you want to install new project package, instead of using pip, run: ```pipenv install <package>``` or for dev packages: ```pipenv install <package> --dev```.        
This will automatically update the **Pipfile and** **Pipfile.lock**.

You can activate project's virtualenv shell by running (from any project's location): ```pipenv shell```        
1. From this shell you can run any pipenv related commands from any directory. 
2. Also, you can execute the application code (since this virtualenv has all the dependencies).

Lastly, you will have to configure your IDE to use this virtualenv.     
You can find out the location of the project's virtualenv by running ```pipenv shell``` and checking the output:
```
Launching subshell in virtual environment…
 . /home/eserskl/.local/share/virtualenvs/backup-EN_Q1m2E/bin/activate
```
Then refer to this [guide - Configure pipenv for an existing Python project](https://www.jetbrains.com/help/pycharm/pipenv.html)

### Tox

So now you want to run the tests, check test coverage, check linter errors, etc...

I suggest to read the **tox** documentation first.        

Then check out the **tox.ini** file.

**Commands to run from CLI:**

* ``pipenv`` - will display manual.
* ``pipenv install`` - will create virtual env with all required dependencies installed for **backup** development.
* ``pipenv install --dev`` - same as above + installs enlisted dev-packages, i.e. test packages.
* ``pipenv install <package>`` - install new dependencies. Pipfile and Pipfile.lock will be updated accordingly. 
* ``pipenv shell`` - will active this virtual env and spawn shell. From here you have access to all installed dependencies.
* ``pipenv run <command>`` - will execute command in virtual environment.
* ``pipenv graph`` - will display all installed dependencies and their sub-dependencies.
* ``pipenv --venv`` - show where the virtual env is installed for this project.
* ``tox`` - run all environments in **envlist**.
* ``tox -e <env>`` - run specific environment.
* ``tox -e py27`` - will run tests.
* ``tox -e coverage`` - will analyse and report test coverage. Also will create **.backup_coverage_html_report/** folder with coverage report.
* ``tox -e clean`` - will remove coverage report folder.
* ``tox -e flake8`` - will analyse code using flake8 linter.
* ``tox -e linters`` - will analyse code using all configured linters under **[testenv:linters]**.
* ``tox -e build`` - will create **dist/** folder with required files for distribution of **backup** package. Based on **setup.py**.

**Environments**

There are some “default” test environments names that we could use (list is available on the tox page) to test our application on different python versions. 

One of them - **py27**. Defines which version of python to use.     
It will build virtualenv with **python2.7** and all dependencies enlisted in **[testenv]** block and run all enlisted commands in the same block.

The rest are custom written environments for different purposes.

* **[testenv]** - run tests with coverage. Generates simple report as CLI output as well as html report.
    * Configuration: **.coveragerc**
* **[testenv:nocoverage]** - run tests without coverage.
* **[testenv:linters]** - combines flake8, pylint and bandit analysis. Reports back violations in CLI.
    * Configuration: 
        * Pylint: **.pylintrc**
        * Bandit: **.bandit.yml** 
        * Flake8: **at the bottom of tox.ini.**
* **[testenv:build]** - creates **dist** folder with **.whl** and **.tar.gz** files.
* **[testenv:docs]** - creates **docs** folder with html documentation from docstrings.

### Release management

1. **setup.py** has to be updated with required dependencies to produce correct **.whl** file.

2. Execute: ```tox -e build``` to create **enmaas_bur-<version>-py2.py3-none-any.whl** file in **dist** folder.

3. Versioning: **src/backup/\_\_init__.py** \_\_version__ has to be updated for new releases.

### Troubleshooting

* I've run ``python cli.py <args>`` but it says <module> is missing.
    * Because you don't have that module installed globally. Instead all modules are installed in your virtual environment.
    * Run ``pipenv run python cli.py <args>`` to run the app locally.
    * Or open pipenv shell ``pipenv shell`` and run ``python cli.py <args>`` from it.

* I've run ``tox`` but is says there are some violations / test failures / other problems...
    * Read violations / failures / other problems and fix them!
    
* I've run ``tox`` but it says that **E   ImportError: No module named <module>**
    * It seems that there is a problem with tox virtual env... delete **.tox/** folder and try again.

* PyCharm/IntelliJ is complaining that **backup** is not a module.
    * Mark **src** folder as **Source Root**
 
* PyCharm/IntelliJ is complaining that there is no valid Python SDK interpreter configured for backup module.
    * Refer to this guide: https://www.jetbrains.com/help/pycharm/pipenv.html
    * Check "Configure pipenv for an existing Python project" section.
    * Execute ``pipenv --venv`` to find where the virtual env is installed for this project.
    * Pipenv default virtual environment location should be something like **~/.local/share/virtualenvs/backup-_<some-sha>_/bin/activate**
    
* PyCharm/IntelliJ is complaining that there is no [gnupg, enum, <othermodule>] installed.
    * Either you didn't configure your Python SDK interpreter as above
    * Or this is a new module and it's not installed in that virtual environment. You can install it via IDE or CLI: ```pipenv install <module_name>``` 