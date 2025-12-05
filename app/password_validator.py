"""
Password validation utilities for enforcing strong password policies.
"""
import re
from typing import Tuple, List

# Common weak passwords to reject
COMMON_PASSWORDS = {
    'password', 'password123', '12345678', 'qwerty', 'abc123', 
    'monkey', '1234567890', 'letmein', 'trustno1', 'dragon',
    'baseball', 'iloveyou', 'master', 'sunshine', 'ashley',
    'bailey', 'passw0rd', 'shadow', '123123', '654321',
    'superman', 'qazwsx', 'michael', 'football', 'admin',
    'changeme', 'changeme123', 'admin123'
}

class PasswordValidator:
    """Validates password strength and complexity."""
    
    def __init__(self, 
                 min_length: int = 12,
                 require_uppercase: bool = True,
                 require_lowercase: bool = True,
                 require_digits: bool = True,
                 require_special: bool = True):
        """
        Initialize password validator with configurable rules.
        
        Args:
            min_length: Minimum password length (default: 12)
            require_uppercase: Require at least one uppercase letter
            require_lowercase: Require at least one lowercase letter
            require_digits: Require at least one digit
            require_special: Require at least one special character
        """
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
    
    def validate(self, password: str, username: str = None) -> Tuple[bool, List[str]]:
        """
        Validate password against all configured rules.
        
        Args:
            password: Password to validate
            username: Optional username to check for similarity
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check minimum length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        # Check for uppercase letters
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check for lowercase letters
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check for digits
        if self.require_digits and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        # Check for special characters
        if self.require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            errors.append("Password must contain at least one special character (!@#$%^&* etc.)")
        
        # Check against common passwords
        if password.lower() in COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a more unique password")
        
        # Check if password contains username
        if username and len(username) >= 3 and username.lower() in password.lower():
            errors.append("Password must not contain your username")
        
        # Check for sequential characters
        if self._has_sequential_chars(password):
            errors.append("Password should not contain sequential characters (e.g., '123', 'abc')")
        
        # Check for repeated characters
        if self._has_repeated_chars(password):
            errors.append("Password should not contain excessive repeated characters")
        
        return (len(errors) == 0, errors)
    
    def get_strength_score(self, password: str) -> int:
        """
        Calculate password strength score from 0-100.
        
        Args:
            password: Password to score
            
        Returns:
            Strength score (0-100)
        """
        score = 0
        
        # Length scoring (up to 30 points)
        if len(password) >= 8:
            score += 10
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Character variety (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            score += 10
        
        # Complexity bonus (up to 30 points)
        char_types = sum([
            bool(re.search(r'[a-z]', password)),
            bool(re.search(r'[A-Z]', password)),
            bool(re.search(r'\d', password)),
            bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
        ])
        
        if char_types >= 3:
            score += 10
        if char_types == 4:
            score += 10
        
        # Uniqueness bonus
        if len(set(password)) / len(password) > 0.7:  # 70% unique characters
            score += 10
        
        # Penalize common passwords
        if password.lower() in COMMON_PASSWORDS:
            score = max(0, score - 50)
        
        # Penalize sequential/repeated patterns
        if self._has_sequential_chars(password):
            score = max(0, score - 20)
        if self._has_repeated_chars(password):
            score = max(0, score - 20)
        
        return min(100, score)
    
    def get_strength_label(self, score: int) -> str:
        """
        Get human-readable strength label for a score.
        
        Args:
            score: Strength score (0-100)
            
        Returns:
            Strength label (Very Weak, Weak, Fair, Strong, Very Strong)
        """
        if score < 20:
            return "Very Weak"
        elif score < 40:
            return "Weak"
        elif score < 60:
            return "Fair"
        elif score < 80:
            return "Strong"
        else:
            return "Very Strong"
    
    def _has_sequential_chars(self, password: str, min_length: int = 3) -> bool:
        """Check if password contains sequential characters."""
        # Check for numeric sequences
        for i in range(len(password) - min_length + 1):
            substr = password[i:i+min_length]
            if substr.isdigit():
                digits = [int(d) for d in substr]
                if all(digits[j] + 1 == digits[j+1] for j in range(len(digits)-1)):
                    return True
                if all(digits[j] - 1 == digits[j+1] for j in range(len(digits)-1)):
                    return True
        
        # Check for alphabetic sequences
        for i in range(len(password) - min_length + 1):
            substr = password[i:i+min_length].lower()
            if substr.isalpha():
                chars = [ord(c) for c in substr]
                if all(chars[j] + 1 == chars[j+1] for j in range(len(chars)-1)):
                    return True
                if all(chars[j] - 1 == chars[j+1] for j in range(len(chars)-1)):
                    return True
        
        return False
    
    def _has_repeated_chars(self, password: str, max_repeats: int = 3) -> bool:
        """Check if password has excessively repeated characters."""
        for i in range(len(password) - max_repeats + 1):
            if len(set(password[i:i+max_repeats])) == 1:
                return True
        return False


# Default validator instance
default_validator = PasswordValidator(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digits=True,
    require_special=True
)


def validate_password(password: str, username: str = None) -> Tuple[bool, List[str]]:
    """
    Validate password using default validator.
    
    Args:
        password: Password to validate
        username: Optional username to check for similarity
        
    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    return default_validator.validate(password, username)


def get_password_strength(password: str) -> Tuple[int, str]:
    """
    Get password strength score and label.
    
    Args:
        password: Password to evaluate
        
    Returns:
        Tuple of (score, label)
    """
    score = default_validator.get_strength_score(password)
    label = default_validator.get_strength_label(score)
    return (score, label)
