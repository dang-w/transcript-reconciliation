# Sourced by the scripts in this directory. Not executable on its own.
#
# The Python environment and the interpreter live outside the home directory and outside the
# repository. Inspect writes the text of every error into the log, with a traceback that names the
# files of the installed packages, and it records the dataset file of a setting by its absolute path.
# With a `.venv` in a repository under a home directory, both would put a home-directory path into a
# log that is published. The directory below belongs to the Homebrew user, so no sudo is needed.
# Each value can be set in the environment before the script runs.
: "${UV_PROJECT_ENVIRONMENT:=/opt/homebrew/var/transcript-reconciliation/venv}"
: "${UV_PYTHON_INSTALL_DIR:=/opt/homebrew/var/transcript-reconciliation/python}"
: "${UV_PYTHON_PREFERENCE:=only-managed}"
export UV_PROJECT_ENVIRONMENT UV_PYTHON_INSTALL_DIR UV_PYTHON_PREFERENCE
