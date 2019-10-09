from setuptools import find_packages
import inspect
import code
import os
import importlib
import warnings


def get_class_docfile_entry(name, add_doc_members=True,
                            add_undoc_members=True,
                            add_show_inheritance=True):
    doc_entry = ":hidden:`{}`".format(name)

    doc_entry += "\n" + "~" * len(doc_entry) + "\n\n"
    doc_entry += ".. autoclass:: {}\n".format(name)
    if add_doc_members:
        doc_entry += "    :members:\n"

    if add_undoc_members:
        doc_entry += "    :undoc-members:\n"

    if add_show_inheritance:
        doc_entry += "    :show-inheritance:\n"

    return doc_entry


def get_function_docfile_entry(name):
    doc_entry = ":hidden:`{}`".format(name)

    doc_entry += "\n" + "~" * len(doc_entry) + "\n\n"
    doc_entry += ".. autofunction:: {}\n".format(name)

    return doc_entry


def get_directories(directory):
    return [os.path.join(directory, x)
            for x in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, x))]



def get_files(directory):
    return [os.path.join(directory, x)
            for x in os.listdir(directory)
            if (os.path.isfile(os.path.join(directory, x))
                and x.endswith(".py") and "__init__" not in x)]


def create_docs_for_file(file: str, add_curr_module=True, **kwargs):
    module_path = file.replace(os.sep, ".").strip(".py")
    module = importlib.import_module(module_path)

    # TODO: Add module docstring
    file_content = ".. role:: hidden\n    :class: hidden-section\n\n"

    if add_curr_module:
        file_content += ".. currentmodule:: {}".format(module_path)

    for member_name, member_object in inspect.getmembers(module):
        if member_name.startswith("_"):
            continue
        if inspect.isclass(member_object):
            file_content += get_class_docfile_entry(name=member_name,
                                                    **kwargs)
        elif inspect.isfunction(member_object):
            file_content += get_function_docfile_entry(name=member_name)

        else:
            warnings.warn(
                "{} is neither a function, nor a class".format(member_name),
                RuntimeWarning)

    return file_content


def process_dir(code_dir, doc_dir, **kwargs):
    os.makedirs(doc_dir)

    files_to_include = []

    for file in get_files(code_dir):
        with open(file.replace(code_dir, doc_dir).replace(".py", ".rst"),
                  "w") as f:
            f.write(create_docs_for_file(file, **kwargs))

        files_to_include.append(file.strip(code_dir).strip(".py"))

