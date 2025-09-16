# Security Configuration for CntxtCS

# File processing limits
MAX_FILE_SIZE_MB = 10
MAX_FILES_TO_PROCESS = 10000
MAX_PROCESSING_TIME_SECONDS = 3600

# Path security
ALLOWED_FILE_EXTENSIONS = ['.cs', '.csproj', '.sln', '.json', '.config', '.xml']
BLOCKED_DIRECTORIES = [
    'bin', 'obj', '.vs', '.git', '.idea', '.vscode', 'packages', 
    'Properties', 'node_modules', '.nuget', 'TestResults', 'Migrations',
    'Debug', 'Release', 'x64', 'x86', 'AnyCPU'
]

# Regex security limits
MAX_REGEX_LENGTH = 1000
REGEX_TIMEOUT_SECONDS = 5

# Output security
MAX_OUTPUT_FILE_SIZE_MB = 100
SANITIZE_OUTPUT = True
ESCAPE_HTML_IN_OUTPUT = True

# Dependency processing
MAX_DEPENDENCY_NAME_LENGTH = 100
MAX_VERSION_STRING_LENGTH = 50
VALIDATE_DEPENDENCY_NAMES = True

# Memory limits
MAX_GRAPH_NODES = 100000
MAX_GRAPH_EDGES = 500000

# Logging security
SANITIZE_ERROR_MESSAGES = True
LOG_FILE_ACCESS_ATTEMPTS = True
MAX_LOG_FILE_SIZE_MB = 10

# Development vs Production settings
DEBUG_MODE = False
VERBOSE_LOGGING = False
EXPOSE_FULL_PATHS = False