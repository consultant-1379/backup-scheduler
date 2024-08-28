##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=W0613
# unused-argument (kwargs)

"""Module is for compressing and decompressing purposes."""

import gzip
import os
from subprocess import Popen
from tarfile import TarError, TarFile

from backup.constants import GZ_SUFFIX, TAR_CMD, TAR_SUFFIX
from backup.exceptions import ExceptionCodes, UtilsException
from backup.utils.decorator import timeit
from backup.utils.fsys import is_valid_path, remove_path
from backup.utils.validator import check_not_empty


@timeit
def compress_file(source_path, output_path=None, mode="w:gz", **kwargs):
    """
    Compress or archive a path using tarfile module.

    This function expects a mode to be either "w:gz", referring to compressing with gzip, or "w",
    which uses no compression.
    Output file is placed in the same directory as the original file by default,
    if no output_path is specified.

    :param source_path: file/folder path to be compressed.
    :param output_path: destination folder of the compressed file.
    :param mode: compression mode to write file (w:gz) or tar mode (w).
    :return compressed file path.
    :raise UtilsException: if the params are not valid or empty.
    """
    is_valid_path(source_path)

    if mode not in ["w", "w:", "w:gz"]:
        raise UtilsException(ExceptionCodes.InvalidCompressionMode, mode)

    if output_path is None or not output_path.strip():
        output_path = os.path.dirname(source_path)

    is_valid_path(output_path)

    if GZ_SUFFIX in mode:
        compressed_file_path = gzip_file(source_path, output_path)
    else:
        compressed_file_path = tar_file(source_path, output_path)

    return compressed_file_path


@timeit
def decompress_file(source_path, output_path, remove_compressed=False, **kwargs):
    """
    Decompress a file using the tar strategy.

    Output file is placed in the same directory as the original file by default,
    if no output_path is specified.

    :param source_path: file to be decompressed.
    :param output_path: file path of the output file.
    :param remove_compressed: flag to inform if the compressed file should be deleted at the end.
    :return decompressed file path.
    :raise UtilsException: if the params are not valid or empty.
    """
    is_valid_path(source_path)

    if output_path is None or not output_path.strip():
        output_path = os.path.dirname(source_path)

    is_valid_path(output_path)

    if is_tar_file(source_path):
        decompressed_file_path = untar_file(source_path, output_path)
    elif is_gzip_file(source_path):
        decompressed_file_path = gunzip_file(source_path, output_path)
    else:
        raise UtilsException(ExceptionCodes.InvalidDecompressionFile, source_path)

    if remove_compressed:
        remove_path(source_path)

    return decompressed_file_path


def gzip_file(file_path, file_destination):
    """
    Compress file using gzip strategy.

    :param file_path: file to be compressed.
    :param file_destination: destination folder.
    :return: full compressed file path.
    :raise UtilsException: if Popen raised an error or if the result wasn't the expected.
    """
    compressed_file_name = "{}.{}".format(os.path.basename(file_path), GZ_SUFFIX)
    compressed_file_path = os.path.join(file_destination, compressed_file_name)
    compress_command = "gzip -r -c {} > {}".format(file_path, compressed_file_path)

    try:
        ret = Popen(compress_command, shell=True).wait()
    except (ValueError, TypeError) as gzip_exp:
        raise UtilsException(parameters=gzip_exp)

    if int(ret) != 0:
        raise UtilsException(ExceptionCodes.GzipCommandError, ret)

    return compressed_file_path


def tar_file(file_path, file_destination):
    """
    Archive file using tar strategy.

    :param file_path: file to be archived.
    :param file_destination: destination folder.
    :return: full archived file path.
    :raise UtilsException: if Popen raised an error or if the result wasn't the expected.
    """
    archived_file_name = "{}.{}".format(os.path.basename(file_path), TAR_SUFFIX)
    tar_file_path = os.path.join(file_destination, archived_file_name)

    compress_command = "{} -cf {} -C {} {}".format(TAR_CMD, tar_file_path,
                                                   os.path.dirname(file_path),
                                                   os.path.basename(file_path))
    try:
        ret = Popen(compress_command, shell=True).wait()
    except (ValueError, TypeError) as tar_exp:
        raise UtilsException(parameters=tar_exp)

    if int(ret) != 0:
        raise UtilsException(ExceptionCodes.TarZipCommandError, ret)

    return tar_file_path


def gunzip_file(file_path, file_destination):
    """
    Decompress file using gzip strategy.

    :param file_path: file to be decompressed.
    :param file_destination: destination folder.
    :return: decompressed file path.
    :raise UtilsException: if Popen raised an error or if the result wasn't the expected.
    """
    decompressed_file_name = os.path.basename(file_path).replace(".{}".format(GZ_SUFFIX), "")
    decompress_command = "gunzip -c {} > {}".format(file_path,
                                                    os.path.join(file_destination,
                                                                 decompressed_file_name))

    try:
        ret = Popen(decompress_command, shell=True).wait()
    except (ValueError, TypeError) as gunzip_exp:
        raise UtilsException(parameters=gunzip_exp)

    if int(ret) != 0:
        raise UtilsException(ExceptionCodes.GunzipCommandError, ret)

    return os.path.join(file_destination, decompressed_file_name)


def untar_file(file_path, file_destination):
    """
    Decompress file using tar strategy.

    :param file_path: file to be decompressed.
    :param file_destination: destination folder.
    :return: decompressed file path.
    :raise UtilsException: if Popen raised an error or if the result wasn't the expected.
    """
    decompress_command = "{} -C {} -xf {}".format(TAR_CMD, file_destination, file_path)

    try:
        ret = Popen(decompress_command, shell=True).wait()
    except (ValueError, TypeError) as untar_exp:
        raise UtilsException(parameters=untar_exp)

    if int(ret) != 0:
        raise UtilsException(ExceptionCodes.TarZipCommandError, ret)

    decompressed_file_name = os.path.basename(file_path).replace(".{}".format(TAR_SUFFIX), "")

    return os.path.join(file_destination, decompressed_file_name)


def is_gzip_file(file_path):
    """
    Check whether the informed file path is in gzip format.

    :param file_path: file path.
    :return: whether the path refers to a gzip file or not.
    :raise UtilsException: if the file_path param is empty or None.
    """
    check_not_empty(file_path)

    with gzip.open(file_path) as compressed_file:
        try:
            compressed_file.read()
        except IOError:
            return False

    return True


def is_tar_file(file_path):
    """
    Check whether the informed file path is in tar format.

    :param file_path: file path.
    :return: whether the path refers to a tar file or not.
    :raise UtilsException: if the file_path param is empty or None.
    """
    check_not_empty(file_path)

    with open(file_path, "r") as compressed_file:
        try:
            TarFile(fileobj=compressed_file)
        except TarError:
            return False

    return True
