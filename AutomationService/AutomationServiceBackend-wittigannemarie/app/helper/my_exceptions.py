class NoTrainingdataException(Exception):
    """Exception raised for missing training or testing data.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Training or testing data missing"):
        self.message = message
        super().__init__(self.message)


class FailedTrainingException(Exception):
    """Exception raised if an error occurs while training.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Training could not conclude. This is likely due to an error in the data."):
        self.message = message
        super().__init__(self.message)


class FailedDocBinException(Exception):
    """Exception raised if an error occurs while generating docbins.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Could not generate Docbins. Please make sure your data is conform, "
                                "correct and conclusive."):
        self.message = message
        super().__init__(self.message)
