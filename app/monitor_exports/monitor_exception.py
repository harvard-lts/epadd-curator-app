class MonitoringException(Exception):
    
    def __init__(self, message, emailaddress):
        super().__init__(message)
        self.emailaddress = emailaddress
        
class ValidationException(Exception):
        pass
    
class InvalidCharacterException(ValidationException):
        pass