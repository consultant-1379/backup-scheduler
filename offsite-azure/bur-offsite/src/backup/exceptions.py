##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=R0915
# too-many-statements

"""
Module for exception handlers.

When raising a custom Exception, use the ExceptionCode to explain the reason for an error.
All custom exceptions should be created with an ExceptionCode and, as optional information,
the parameters that were the cause of error.

If an ExceptionCode isn't informed, a default one is used.
"""

from enum import Enum


class ExceptionCodes(Enum):
    """Enum custom codes for errors."""

    DefaultExceptionCode = 30
    OperationNotSupported = 31
    InvalidPath = 32
    EmptyValue = 33
    InvalidValue = 34
    CannotCreatePath = 35
    MissingOffSiteSection = 36
    MissingOffSiteParameters = 37
    InvalidIPAddress = 38
    CannotAccessHost = 39
    MissingCustomerSection = 40
    ErrorSendingEmail = 41
    InvalidCompressionMode = 42
    MissingBackupDelaySection = 43
    MissingGnupgSection = 44
    MissingSupportContactSection = 45
    MissingOnSiteSection = 46
    InvalidDecompressionFile = 47
    GzipCommandError = 48
    TarZipCommandError = 49
    GunzipCommandError = 50
    ConfigurationFileReadError = 51
    ConfigurationFileParsingError = 52
    ConfigurationFileOptionError = 53
    NotEnoughFreeDiskSpace = 54
    ElementNotFound = 55
    InvalidTimeUnit = 56
    InvalidTimeFormat = 57
    InvalidFile = 58
    InvalidFolder = 59
    CannotRemovePath = 60
    CannotParseValue = 61
    MissingNumberOfParameter = 62
    RsyncTransferNumberFilesDiffer = 63
    NoFilesToSend = 64
    ExceedTryOuts = 65
    PlatformNotSupportedForGPG = 66
    CannotCreateGPGKey = 67
    EncryptError = 68
    CannotRemoveFile = 69
    DecryptError = 70
    InvalidGPGFile = 71
    NoBackupsToProcess = 72
    ProcessBackupListErrors = 73
    FailedToGetProcessedVolsNamesOffsite = 74
    NoSuchBackupTag = 75
    CannotUnwrapperObject = 76
    NoVolumeListForBackup = 77
    NoMetadataForBackup = 78
    MissingBackupOKFlag = 79
    BackupAlreadyDownloaded = 80
    DownloadProcessFailed = 81
    MissingVolume = 82
    MetadataValidationFailed = 83
    WrongTypeError = 84
    MissingBackupTagCustomerNameForDownload = 85
    MissingCustomerNameForUpload = 86
    InvalidRetentionValue = 87
    InvalidSiteLocations = 88
    ErrorSortingOffsiteBackupList = 89
    AzCopyExecutionFailed = 90
    AzCopyCommandFailed = 91


def get_exception_message(code=None):
    """
    Get the exception messages for each ExceptionCode.

    :param code: ExceptionCode that the message is sought for.
    :return: dictionary of messages and exception codes or a message, if exception code is informed.
    """
    msgs = dict()

    msgs[ExceptionCodes.DefaultExceptionCode] = "Something went wrong."
    msgs[ExceptionCodes.OperationNotSupported] = "Operation Code informed is not supported."
    msgs[ExceptionCodes.InvalidPath] = "Path informed is not a valid formatted folder or file."
    msgs[ExceptionCodes.InvalidFile] = "Path informed is not a valid existent file."
    msgs[ExceptionCodes.InvalidFolder] = "Path informed is not a valid existent folder."
    msgs[ExceptionCodes.EmptyValue] = "Value not informed."
    msgs[ExceptionCodes.CannotCreatePath] = "Path informed cannot be created."
    msgs[ExceptionCodes.MissingOffSiteSection] = "Off-site section not defined in the " \
                                                 "configuration file."
    msgs[ExceptionCodes.MissingOffSiteParameters] = "Off-site section has missing parameters."
    msgs[ExceptionCodes.MissingOnSiteSection] = "On-site section not defined in the " \
                                                "configuration file."
    msgs[ExceptionCodes.MissingCustomerSection] = "Customers section not defined in the " \
                                                  "configuration file."
    msgs[ExceptionCodes.ErrorSendingEmail] = "Failed sending e-mail."
    msgs[ExceptionCodes.InvalidCompressionMode] = "Invalid compression mode. Accepted are: " \
                                                  "'w', 'w:' or 'w:gz'"
    msgs[ExceptionCodes.ConfigurationFileReadError] = "Cannot read configuration file."
    msgs[ExceptionCodes.ConfigurationFileParsingError] = "Cannot parse configuration file."
    msgs[ExceptionCodes.ConfigurationFileOptionError] = "Cannot read option from " \
                                                        "configuration file."
    msgs[ExceptionCodes.InvalidDecompressionFile] = "Invalid file format for decompressing. " \
                                                    "Supported files are .tar and .gz"
    msgs[ExceptionCodes.GzipCommandError] = "Gzip command returned error code."
    msgs[ExceptionCodes.TarZipCommandError] = "Tar command returned error code."
    msgs[ExceptionCodes.GunzipCommandError] = "Gunzip command returned error code."
    msgs[ExceptionCodes.NotEnoughFreeDiskSpace] = "Path doesn't have enough disk space for backup."
    msgs[ExceptionCodes.ElementNotFound] = "There is no element related to the key informed."
    msgs[ExceptionCodes.InvalidTimeUnit] = "Invalid time unit (must be 's' or 'h' or 'm')."
    msgs[ExceptionCodes.InvalidTimeFormat] = "Wrong format. It must be number + time unit " \
                                             "(i.e. 3s or 4m or 5h)."
    msgs[ExceptionCodes.InvalidValue] = "Invalid value. Check value type or range."
    msgs[ExceptionCodes.CannotRemovePath] = "Path(s) informed cannot be removed."
    msgs[ExceptionCodes.CannotParseValue] = "Value informed cannot be parsed."
    msgs[ExceptionCodes.MissingNumberOfParameter] = "Line does not contain a number of measurement."
    msgs[ExceptionCodes.RsyncTransferNumberFilesDiffer] = "Number of files transferred differs " \
                                                          "from files on origin path and " \
                                                          "destination path."
    msgs[ExceptionCodes.NoFilesToSend] = "There is no file to be sent."
    msgs[ExceptionCodes.ExceedTryOuts] = "The limit of tries has been reached."
    msgs[ExceptionCodes.PlatformNotSupportedForGPG] = "Platform not supported for GNUPG " \
                                                      "encryption tool."
    msgs[ExceptionCodes.EncryptError] = "File encryption could not be completed."
    msgs[ExceptionCodes.CannotRemoveFile] = "File cannot be removed."
    msgs[ExceptionCodes.DecryptError] = "File decryption could not be completed."
    msgs[ExceptionCodes.InvalidGPGFile] = "Not a valid GPG encrypted file."
    msgs[ExceptionCodes.CannotCreateGPGKey] = "GPG key could not be created."
    msgs[ExceptionCodes.NoBackupsToProcess] = "No backups to process."
    msgs[ExceptionCodes.ProcessBackupListErrors] = "Process backup list has a list of errors."
    msgs[ExceptionCodes.FailedToGetProcessedVolsNamesOffsite] = "Failed to get processed volumes " \
                                                                "names for the off-site backup."
    msgs[ExceptionCodes.NoSuchBackupTag] = "Backup tag not found."
    msgs[ExceptionCodes.CannotUnwrapperObject] = "Could not unwrap backup handler object."
    msgs[ExceptionCodes.NoVolumeListForBackup] = "No volume list found for the backup."
    msgs[ExceptionCodes.NoMetadataForBackup] = "No metadata/descriptor file found for the backup."
    msgs[ExceptionCodes.MissingBackupOKFlag] = "Backup OK flag not found for the backup."
    msgs[ExceptionCodes.BackupAlreadyDownloaded] = "A backup with the same tag is already " \
                                                   "downloaded in the download path."
    msgs[ExceptionCodes.DownloadProcessFailed] = "Failed to process downloaded backup."
    msgs[ExceptionCodes.MissingVolume] = "Volume not found in path."
    msgs[ExceptionCodes.MetadataValidationFailed] = "Downloaded backup could not be validated " \
                                                    "against metadata."
    msgs[ExceptionCodes.WrongTypeError] = "Expected input has a wrong type."
    msgs[ExceptionCodes.MissingBackupTagCustomerNameForDownload] = "Backup tag or customer name " \
                                                                   "needed to proceed with " \
                                                                   "backup download."
    msgs[ExceptionCodes.MissingCustomerNameForUpload] = "Customer name needed to proceed with " \
                                                        "backup upload."
    msgs[ExceptionCodes.InvalidRetentionValue] = "Retention value must be 1 or greater."
    msgs[ExceptionCodes.MissingGnupgSection] = "GNUPG section not defined in the " \
                                               "configuration file."
    msgs[ExceptionCodes.InvalidSiteLocations] = "Couldn't validate on-site/off-site locations."
    msgs[ExceptionCodes.ErrorSortingOffsiteBackupList] = "Couldn't sort the list of " \
                                                         "backups from the offsite location."
    msgs[ExceptionCodes.AzCopyExecutionFailed] = "AzCopy execution failed"
    msgs[ExceptionCodes.AzCopyCommandFailed] = "AzCopy Command returned Non zero error code"

    try:
        return msgs[code]
    except KeyError:
        return msgs[ExceptionCodes.DefaultExceptionCode]


class BurException(Exception):
    """Class for defining the structure of custom exceptions."""

    def __init__(self, message, code):
        """
        Initialize BurException.

        :param code: error code.
        :param message: description of an error code.
        """
        super(BurException, self).__init__(message, code)
        self.message = message
        self.code = code

    def __str__(self):
        """Define the string format of a BurException object."""
        return "Error Code {}. {}".format(self.code.value, self.message)

    def __repr__(self):
        """Define the basic representation of a BurException object."""
        return self.__str__()


class AzCopyException(BurException):
    """Exception class to refer error raised from utils package."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a RsyncManagerException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(AzCopyException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message

        def __str__(self):
            """Define the string format of a BurException object."""
            return "Error Code {}. {}".format(self.code, self.message)

        def __repr__(self):
            """Define the basic representation of a BurException object."""
            return self.__str__()


class InputValidatorsException(BurException):
    """Exception class to refer error raised from bur_input_validators.py script."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize an InputValidatorsException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(InputValidatorsException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class NotificationHandlerException(BurException):
    """Exception class to refer error raised from NotificationHandler."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a NotificationHandlerException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(NotificationHandlerException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class BackupSettingsException(BurException):
    """Exception class to refer error raised from backup_settings.py script."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a BackupSettingsException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(BackupSettingsException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class UtilsException(BurException):
    """Exception class to refer error raised from utils package."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize an UtilsException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(UtilsException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class RsyncException(BurException):
    """Exception class to refer error raised from utils package."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a RsyncManagerException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(RsyncException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class GnupgException(BurException):
    """Exception class to refer error raised from utils package."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a GnupgException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(GnupgException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class UploadBackupException(BurException):
    """Exception class to refer to errors raised from local_backup_handler.py ."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize an UploadBackupException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(UploadBackupException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message


class DownloadBackupException(BurException):
    """Exception class to refer to errors raised from local_backup_handler.py ."""

    def __init__(self, code=None, parameters=None):
        """
        Initialize a DownloadBackupException.

        :param code: error code.
        :param parameters: input variable that caused the error.
        """
        code = code if code else ExceptionCodes.DefaultExceptionCode
        message = get_exception_message(code)
        super(DownloadBackupException, self).__init__(message, code)
        self.code = code
        self.parameters = parameters
        if self.parameters:
            self.message = "{} ({})".format(message, self.parameters)
        else:
            self.message = message
