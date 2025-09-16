# CntxtCS.py - C# codebase analyzer that generates comprehensive knowledge graphs optimized for LLM context windows

import os
import re
import sys
import json
import time
import hashlib
import pathlib
import networkx as nx
from networkx.readwrite import json_graph
from typing import Dict, List, Optional, Any


class CSCodeKnowledgeGraph:
    def __init__(self, directory: str, max_file_size_mb: int = 10, max_files: int = 10000):
        """Initialize the knowledge graph generator.

        Args:
            directory: Root directory of the C# codebase.
            max_file_size_mb: Maximum file size in MB to process (default: 10MB)
            max_files: Maximum number of files to process (default: 10,000)
        """
        # Security: Validate and sanitize directory path
        self.directory = self._validate_directory_path(directory)
        self.graph = nx.DiGraph()
        self.class_methods: Dict[str, List[str]] = {}
        self.method_params: Dict[str, List[Dict[str, Any]]] = {}
        self.method_returns: Dict[str, str] = {}
        self.files_processed = 0
        self.total_files = 0
        self.dirs_processed = 0

        # Security: Resource limits
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.start_time = time.time()
        self.max_processing_time = 3600  # 1 hour maximum processing time

        # Map of analyzed files to prevent circular dependencies.
        self.analyzed_files = set()

        # Map exported entities to their defining files.
        self.exports_map: Dict[str, List[str]] = {}

        # Directories to ignore during analysis.
        self.ignored_directories = set([
            'bin', 'obj', '.vs', '.git', '.idea', '.vscode', 'packages', 'Properties',
            'node_modules', '.nuget', 'TestResults', 'Migrations'
        ])

        # Files to ignore during analysis.
        self.ignored_files = set([
            '.gitignore',
            '.gitattributes',
            '.editorconfig',
        ])

        # For processing dependencies
        self.dependencies: Dict[str, List[str]] = {}

        # Counters for statistics
        self.total_namespaces = 0
        self.total_classes = 0
        self.total_methods = 0
        self.total_interfaces = 0
        self.total_enums = 0
        self.total_structs = 0
        self.total_dependencies = set()
        self.total_usings = 0
    
    def _validate_directory_path(self, directory: str) -> str:
        """Validate and sanitize directory path to prevent path traversal attacks.
        
        Args:
            directory: User-provided directory path
            
        Returns:
            Validated and canonicalized directory path
            
        Raises:
            ValueError: If path is invalid or potentially malicious
        """
        if not directory or not directory.strip():
            raise ValueError("Directory path cannot be empty")
        
        # Remove leading/trailing whitespace
        directory = directory.strip()
        
        # Convert to Path object for safer handling
        try:
            path = pathlib.Path(directory).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid directory path: {e}")
        
        # Check if path exists and is a directory
        if not path.exists():
            raise ValueError(f"Directory does not exist: {path}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        # Convert back to string for compatibility
        return str(path)
    
    def _is_safe_file(self, file_path: str) -> bool:
        """Check if file is safe to process.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is safe to process, False otherwise
        """
        try:
            path = pathlib.Path(file_path)
            
            # Check if it's a symbolic link (potential security risk)
            if path.is_symlink():
                return False
            
            # Check file size
            if path.stat().st_size > self.max_file_size_bytes:
                print(f"Warning: Skipping large file {file_path} ({path.stat().st_size} bytes)")
                return False
            
            # Check if we've reached file limit
            if self.files_processed >= self.max_files:
                print(f"Warning: Maximum file limit ({self.max_files}) reached")
                return False
            
            # Check processing time limit
            if time.time() - self.start_time > self.max_processing_time:
                print(f"Warning: Maximum processing time exceeded")
                return False
            
            return True
            
        except (OSError, ValueError):
            return False
    
    def _sanitize_error_message(self, file_path: str, error: str) -> str:
        """Sanitize error messages to prevent information disclosure.
        
        Args:
            file_path: Original file path
            error: Original error message
            
        Returns:
            Sanitized error message
        """
        # Create a hash of the file path for logging without disclosure
        path_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
        
        # Remove sensitive path information from error message
        sanitized_error = str(error).replace(file_path, f"file_{path_hash}")
        sanitized_error = re.sub(r'/[^/\s]+', '/***', sanitized_error)
        
        return f"Error processing file_{path_hash}: {sanitized_error}"

    def analyze_codebase(self):
        """Analyze the C# codebase to extract files, usings, classes, methods, and their relationships."""
        # First pass to count total files
        print("\nCounting files...")
        for root, dirs, files in os.walk(self.directory):
            # Remove ignored directories from dirs in-place to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            # Skip if current directory is in ignored directories
            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]
            self.total_files += sum(1 for f in files if f not in self.ignored_files and f.endswith(".cs"))

        print(f"Found {self.total_files} C# files to process")
        print("\nProcessing files...")

        # Second pass to process files
        for root, dirs, files in os.walk(self.directory):
            # Remove ignored directories from dirs in-place to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            # Skip if current directory is in ignored directories
            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue

            # Display current directory
            rel_path = os.path.relpath(root, self.directory)
            self.dirs_processed += 1
            print(f"\rProcessing directory [{self.dirs_processed}]: {rel_path}", end="")

            for file in files:
                if file in self.ignored_files:
                    continue
                if file.endswith(".cs"):
                    file_path = os.path.join(root, file)
                    self._process_file(file_path)
                elif file.endswith((".csproj", "packages.config", "packages.lock.json")):
                    file_path = os.path.join(root, file)
                    self._process_dependency_file(file_path)

        print(f"\n\nCompleted processing {self.files_processed} files across {self.dirs_processed} directories")

    def _process_file(self, file_path: str):
        """Process a file to detect usings, namespaces, classes, methods, etc."""
        if file_path in self.analyzed_files:
            return

        # Security: Check if file is safe to process
        if not self._is_safe_file(file_path):
            return

        try:
            self.files_processed += 1
            relative_path = os.path.relpath(file_path, self.directory)
            print(f"\rProcessing file [{self.files_processed}/{self.total_files}]: {relative_path}", end="", flush=True)

            # Security: Safe file reading with size limits
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(self.max_file_size_bytes)

            relative_path = os.path.relpath(file_path, self.directory)
            file_node = f"File: {relative_path}"

            # Add to analyzed files set.
            self.analyzed_files.add(file_path)

            # Add file node if it doesn't exist.
            if not self.graph.has_node(file_node):
                self.graph.add_node(file_node, type="file", path=relative_path)

            # Process the file contents.
            self._process_usings(content, file_node)
            self._process_namespaces(content, file_node)

        except Exception as e:
            # Security: Sanitize error messages
            sanitized_error = self._sanitize_error_message(file_path, str(e))
            print(sanitized_error, file=sys.stderr)

    def _process_usings(self, content: str, file_node: str):
        """Process using statements in the content."""
        # Security: More efficient regex pattern to prevent ReDoS
        using_pattern = r'using\s+(?:static\s+)?([\w\.]{1,200})\s*;'

        try:
            matches = re.finditer(using_pattern, content, re.MULTILINE)
            for match in matches:
                namespace = match.group(1)
                
                # Security: Validate namespace format
                if not re.match(r'^[\w\.]+$', namespace):
                    continue
                
                using_node = f"Namespace: {namespace}"

                if not self.graph.has_node(using_node):
                    self.graph.add_node(using_node, type="namespace", name=namespace)

                self.graph.add_edge(file_node, using_node, relation="USES_NAMESPACE")
                self.total_usings += 1

                # Track dependencies if it's an external library
                if not namespace.startswith('System') and '.' in namespace:
                    self.total_dependencies.add(namespace.split('.')[0])

        except Exception as e:
            print(f"Error processing using statements: {str(e)}", file=sys.stderr)

    def _process_namespaces(self, content: str, file_node: str):
        """Process namespace declarations and their contents."""
        # Security: More efficient regex pattern to prevent ReDoS
        # Process namespaces line by line instead of using greedy matching
        lines = content.split('\n')
        namespace_stack = []
        brace_count = 0
        current_namespace = None
        namespace_content = []
        
        for line in lines:
            stripped_line = line.strip()
            
            # Check for namespace declaration
            namespace_match = re.match(r'namespace\s+([\w\.]{1,100})\s*\{?', stripped_line)
            if namespace_match:
                namespace_name = namespace_match.group(1)
                
                # Security: Validate namespace format
                if not re.match(r'^[\w\.]+$', namespace_name):
                    continue
                
                current_namespace = namespace_name
                namespace_stack.append(namespace_name)
                namespace_content = []
                
                # Create namespace node
                namespace_node = f"Namespace: {namespace_name}"
                if not self.graph.has_node(namespace_node):
                    self.graph.add_node(namespace_node, type="namespace", name=namespace_name)
                
                self.graph.add_edge(file_node, namespace_node, relation="CONTAINS_NAMESPACE")
                self.total_namespaces += 1
                
                if '{' in stripped_line:
                    brace_count += stripped_line.count('{')
                    brace_count -= stripped_line.count('}')
                continue
            
            if current_namespace:
                namespace_content.append(line)
                brace_count += stripped_line.count('{')
                brace_count -= stripped_line.count('}')
                
                if brace_count <= 0 and namespace_stack:
                    # End of namespace
                    namespace_body = '\n'.join(namespace_content)
                    namespace_node = f"Namespace: {current_namespace}"
                    
                    try:
                        # Process contents inside namespace
                        self._process_classes(namespace_body, namespace_node)
                        self._process_interfaces(namespace_body, namespace_node)
                        self._process_enums(namespace_body, namespace_node)
                        self._process_structs(namespace_body, namespace_node)
                    except Exception as e:
                        print(f"Error processing namespace {current_namespace}: {str(e)}", file=sys.stderr)
                    
                    namespace_stack.pop()
                    current_namespace = namespace_stack[-1] if namespace_stack else None
                    namespace_content = []
                    brace_count = 0

    def _process_classes(self, content: str, parent_node: str):
        """Process class declarations."""
        # Security: More efficient regex pattern to prevent ReDoS
        class_pattern = r'(public|protected|internal|private)?\s*(abstract|sealed|static|partial)?\s*class\s+(\w{1,100})(?:\s*:\s*([\w,\s]{1,200}))?\s*\{'

        matches = re.finditer(class_pattern, content, re.MULTILINE)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'internal'
                modifiers = match.group(2) or ''
                class_name = match.group(3)
                inherits = match.group(4)
                
                # Security: Validate class name format
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', class_name):
                    continue
                
                class_node = f"Class: {class_name}"

                if not self.graph.has_node(class_node):
                    self.graph.add_node(
                        class_node,
                        type="class",
                        name=class_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        inherits=inherits.strip() if inherits else None
                    )

                self.graph.add_edge(parent_node, class_node, relation="CONTAINS_CLASS")
                self.total_classes += 1

                # Get class body to process methods, properties, etc.
                class_body = self._extract_block(content, match.end() - 1)
                if len(class_body) < 50000:  # Security: Limit processed content size
                    self._process_methods(class_body, class_node)
                    self._process_properties(class_body, class_node)
                    self._process_events(class_body, class_node)
                    self._process_fields(class_body, class_node)

                # Handle inheritance
                if inherits:
                    base_classes = [b.strip() for b in inherits.split(',') if b.strip()]
                    for base in base_classes[:10]:  # Security: Limit inheritance chain
                        # Security: Validate base class name
                        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', base):
                            base_node = f"Class: {base}"
                            if not self.graph.has_node(base_node):
                                self.graph.add_node(base_node, type="class", name=base)
                            self.graph.add_edge(class_node, base_node, relation="INHERITS")

            except Exception as e:
                print(f"Error processing class: {str(e)}", file=sys.stderr)

    def _process_methods(self, content: str, class_node: str):
        """Process method declarations within a class."""
        method_pattern = r'(public|protected|internal|private)?\s*(static|virtual|override|abstract|async|sealed|new|extern)?\s*([\w\<\>\[\]]+)\s+(\w+)\s*\(([^\)]*)\)\s*{'

        matches = re.finditer(method_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'private'
                modifiers = match.group(2) or ''
                return_type = match.group(3)
                method_name = match.group(4)
                parameters = match.group(5)
                method_node = f"Method: {method_name} ({class_node})"

                if not self.graph.has_node(method_node):
                    self.graph.add_node(
                        method_node,
                        type="method",
                        name=method_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        return_type=return_type.strip(),
                        parameters=self._parse_parameters(parameters)
                    )

                self.graph.add_edge(class_node, method_node, relation="HAS_METHOD")

                # Track class methods.
                if class_node not in self.class_methods:
                    self.class_methods[class_node] = []
                self.class_methods[class_node].append(method_name)

                # Track method parameters and returns.
                self.method_params[method_node] = self._parse_parameters(parameters)
                self.method_returns[method_node] = return_type.strip()

                self.total_methods += 1

            except Exception as e:
                print(f"Error processing method {method_name}: {str(e)}", file=sys.stderr)

    def _process_properties(self, content: str, class_node: str):
        """Process property declarations within a class."""
        property_pattern = r'(public|protected|internal|private)?\s*(static|virtual|override|abstract|sealed|new|extern)?\s*([\w\<\>\[\]]+)\s+(\w+)\s*{\s*(get;|set;|get; set;|set; get;)\s*}'

        matches = re.finditer(property_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'private'
                modifiers = match.group(2) or ''
                property_type = match.group(3)
                property_name = match.group(4)
                accessors = match.group(5)
                property_node = f"Property: {property_name} ({class_node})"

                if not self.graph.has_node(property_node):
                    self.graph.add_node(
                        property_node,
                        type="property",
                        name=property_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        property_type=property_type.strip(),
                        accessors=accessors.strip()
                    )

                self.graph.add_edge(class_node, property_node, relation="HAS_PROPERTY")

            except Exception as e:
                print(f"Error processing property {property_name}: {str(e)}", file=sys.stderr)

    def _process_events(self, content: str, class_node: str):
        """Process event declarations within a class."""
        event_pattern = r'(public|protected|internal|private)?\s*(static|virtual|override|abstract|sealed|new|extern)?\s*event\s+([\w\<\>\[\]]+)\s+(\w+)\s*;'

        matches = re.finditer(event_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'private'
                modifiers = match.group(2) or ''
                event_type = match.group(3)
                event_name = match.group(4)
                event_node = f"Event: {event_name} ({class_node})"

                if not self.graph.has_node(event_node):
                    self.graph.add_node(
                        event_node,
                        type="event",
                        name=event_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        event_type=event_type.strip()
                    )

                self.graph.add_edge(class_node, event_node, relation="HAS_EVENT")

            except Exception as e:
                print(f"Error processing event {event_name}: {str(e)}", file=sys.stderr)

    def _process_fields(self, content: str, class_node: str):
        """Process field declarations within a class."""
        field_pattern = r'(public|protected|internal|private)?\s*(static|readonly|const|volatile)?\s*([\w\<\>\[\]]+)\s+(\w+)\s*(=\s*[^;]+)?;'

        matches = re.finditer(field_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'private'
                modifiers = match.group(2) or ''
                field_type = match.group(3)
                field_name = match.group(4)
                field_node = f"Field: {field_name} ({class_node})"

                if not self.graph.has_node(field_node):
                    self.graph.add_node(
                        field_node,
                        type="field",
                        name=field_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        field_type=field_type.strip()
                    )

                self.graph.add_edge(class_node, field_node, relation="HAS_FIELD")

            except Exception as e:
                print(f"Error processing field {field_name}: {str(e)}", file=sys.stderr)

    def _process_interfaces(self, content: str, parent_node: str):
        """Process interface declarations."""
        interface_pattern = r'(public|protected|internal|private)?\s*(partial)?\s*interface\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*{'

        matches = re.finditer(interface_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'internal'
                modifiers = match.group(2) or ''
                interface_name = match.group(3)
                inherits = match.group(4)
                interface_node = f"Interface: {interface_name}"

                if not self.graph.has_node(interface_node):
                    self.graph.add_node(
                        interface_node,
                        type="interface",
                        name=interface_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        inherits=inherits.strip() if inherits else None
                    )

                self.graph.add_edge(parent_node, interface_node, relation="CONTAINS_INTERFACE")
                self.total_interfaces += 1

                # Get interface body to process methods, properties, etc.
                interface_body = self._extract_block(content, match.end() - 1)
                self._process_interface_members(interface_body, interface_node)

                # Handle inheritance
                if inherits:
                    base_interfaces = [b.strip() for b in inherits.split(',')]
                    for base in base_interfaces:
                        base_node = f"Interface: {base}"
                        if not self.graph.has_node(base_node):
                            self.graph.add_node(base_node, type="interface", name=base)
                        self.graph.add_edge(interface_node, base_node, relation="INHERITS_INTERFACE")

            except Exception as e:
                print(f"Error processing interface {interface_name}: {str(e)}", file=sys.stderr)

    def _process_interface_members(self, content: str, interface_node: str):
        """Process members of an interface."""
        # Interfaces can contain methods, properties, events, indexers
        # For simplicity, we'll process methods and properties

        # Methods
        method_pattern = r'([\w\<\>\[\]]+)\s+(\w+)\s*\(([^\)]*)\)\s*;'

        matches = re.finditer(method_pattern, content)
        for match in matches:
            try:
                return_type = match.group(1)
                method_name = match.group(2)
                parameters = match.group(3)
                method_node = f"Method: {method_name} ({interface_node})"

                if not self.graph.has_node(method_node):
                    self.graph.add_node(
                        method_node,
                        type="method",
                        name=method_name,
                        access_modifier='public',
                        modifiers='abstract',
                        return_type=return_type.strip(),
                        parameters=self._parse_parameters(parameters)
                    )

                self.graph.add_edge(interface_node, method_node, relation="HAS_METHOD")

                # Track method parameters and returns.
                self.method_params[method_node] = self._parse_parameters(parameters)
                self.method_returns[method_node] = return_type.strip()

            except Exception as e:
                print(f"Error processing interface method {method_name}: {str(e)}", file=sys.stderr)

        # Properties
        property_pattern = r'([\w\<\>\[\]]+)\s+(\w+)\s*{\s*(get;\s*set;|get;|set;)\s*}'

        matches = re.finditer(property_pattern, content)
        for match in matches:
            try:
                property_type = match.group(1)
                property_name = match.group(2)
                accessors = match.group(3)
                property_node = f"Property: {property_name} ({interface_node})"

                if not self.graph.has_node(property_node):
                    self.graph.add_node(
                        property_node,
                        type="property",
                        name=property_name,
                        access_modifier='public',
                        modifiers='abstract',
                        property_type=property_type.strip(),
                        accessors=accessors.strip()
                    )

                self.graph.add_edge(interface_node, property_node, relation="HAS_PROPERTY")

            except Exception as e:
                print(f"Error processing interface property {property_name}: {str(e)}", file=sys.stderr)

    def _process_enums(self, content: str, parent_node: str):
        """Process enum declarations."""
        # Security: More efficient approach to avoid ReDoS
        lines = content.split('\n')
        enum_start = None
        brace_count = 0
        enum_content = []
        
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            
            # Check for enum declaration
            enum_match = re.match(r'(public|protected|internal|private)?\s*enum\s+(\w{1,100})\s*\{?', stripped_line)
            if enum_match:
                access_modifier = enum_match.group(1) or 'internal'
                enum_name = enum_match.group(2)
                
                # Security: Validate enum name format
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', enum_name):
                    continue
                
                enum_start = i
                enum_content = []
                brace_count = 0
                
                # Create enum node
                enum_node = f"Enum: {enum_name}"
                if not self.graph.has_node(enum_node):
                    self.graph.add_node(
                        enum_node,
                        type="enum",
                        name=enum_name,
                        access_modifier=access_modifier
                    )
                
                self.graph.add_edge(parent_node, enum_node, relation="CONTAINS_ENUM")
                self.total_enums += 1
                
                if '{' in stripped_line:
                    brace_count += stripped_line.count('{')
                    brace_count -= stripped_line.count('}')
                continue
            
            if enum_start is not None:
                enum_content.append(line)
                brace_count += stripped_line.count('{')
                brace_count -= stripped_line.count('}')
                
                if brace_count <= 0:
                    # End of enum, process members
                    enum_body = '\n'.join(enum_content)
                    
                    try:
                        # Security: Limit enum processing
                        if len(enum_body) < 10000:  # Limit size
                            # Process enum members more safely
                            member_lines = []
                            for line in enum_body.split('\n'):
                                cleaned = line.strip().rstrip(',').strip()
                                if cleaned and not cleaned.startswith('//') and not cleaned.startswith('/*'):
                                    # Security: Validate member format
                                    member_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)', cleaned)
                                    if member_match:
                                        member_lines.append(member_match.group(1))
                            
                            # Add enum members (limit to reasonable number)
                            for member in member_lines[:100]:  # Security: Limit member count
                                member_node = f"EnumMember: {member} ({enum_node})"
                                if not self.graph.has_node(member_node):
                                    self.graph.add_node(
                                        member_node,
                                        type="enum_member",
                                        name=member
                                    )
                                self.graph.add_edge(enum_node, member_node, relation="HAS_MEMBER")
                    
                    except Exception as e:
                        print(f"Error processing enum members: {str(e)}", file=sys.stderr)
                    
                    enum_start = None
                    enum_content = []
                    brace_count = 0

    def _process_structs(self, content: str, parent_node: str):
        """Process struct declarations."""
        struct_pattern = r'(public|protected|internal|private)?\s*(partial)?\s*struct\s+(\w+)(?:\s*:\s*([\w,\s]+))?\s*{'

        matches = re.finditer(struct_pattern, content)
        for match in matches:
            try:
                access_modifier = match.group(1) or 'internal'
                modifiers = match.group(2) or ''
                struct_name = match.group(3)
                inherits = match.group(4)
                struct_node = f"Struct: {struct_name}"

                if not self.graph.has_node(struct_node):
                    self.graph.add_node(
                        struct_node,
                        type="struct",
                        name=struct_name,
                        access_modifier=access_modifier,
                        modifiers=modifiers.strip(),
                        inherits=inherits.strip() if inherits else None
                    )

                self.graph.add_edge(parent_node, struct_node, relation="CONTAINS_STRUCT")
                self.total_structs += 1

                # Get struct body to process methods, properties, etc.
                struct_body = self._extract_block(content, match.end() - 1)
                self._process_methods(struct_body, struct_node)
                self._process_properties(struct_body, struct_node)
                self._process_fields(struct_body, struct_node)

                # Handle inheritance
                if inherits:
                    base_types = [b.strip() for b in inherits.split(',')]
                    for base in base_types:
                        base_node = f"Struct: {base}"
                        if not self.graph.has_node(base_node):
                            self.graph.add_node(base_node, type="struct", name=base)
                        self.graph.add_edge(struct_node, base_node, relation="INHERITS")

            except Exception as e:
                print(f"Error processing struct {struct_name}: {str(e)}", file=sys.stderr)

    def _parse_parameters(self, params_str: str) -> List[Dict[str, Any]]:
        """Parse method parameters including types and default values."""
        if not params_str:
            return []

        params = []
        depth = 0
        current_param = ""

        for char in params_str:
            if char in '<([{':
                depth += 1
            elif char in '>)]}':
                depth -= 1
            elif char == ',' and depth == 0:
                if current_param.strip():
                    params.append(self._parse_single_parameter(current_param.strip()))
                current_param = ""
                continue
            current_param += char

        if current_param.strip():
            params.append(self._parse_single_parameter(current_param.strip()))

        return params

    def _parse_single_parameter(self, param: str) -> Dict[str, Any]:
        """Parse a single parameter with its type and default value."""
        param_dict: Dict[str, Any] = {"definition": param}

        # Handle parameter modifiers (ref, out, in, params)
        modifier_match = re.match(r'(ref|out|in|params)\s+([\w\<\>\[\]]+)\s+(\w+)', param)
        if modifier_match:
            param_dict["modifier"] = modifier_match.group(1)
            param_dict["type"] = modifier_match.group(2)
            param_dict["name"] = modifier_match.group(3)
        else:
            type_name_match = re.match(r'([\w\<\>\[\]]+)\s+(\w+)', param)
            if type_name_match:
                param_dict["type"] = type_name_match.group(1)
                param_dict["name"] = type_name_match.group(2)
            else:
                param_dict["name"] = param.strip()

        # Handle default values
        default_match = re.match(r'([\w\<\>\[\]]+\s+\w+)\s*=\s*(.+)', param)
        if default_match:
            param_dict["default"] = default_match.group(2).strip()

        return param_dict

    def _extract_block(self, content: str, start_index: int) -> str:
        """Extract code block starting from the given index."""
        stack = []
        block = ''
        for i in range(start_index, len(content)):
            char = content[i]
            block += char
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                else:
                    break
            if not stack:
                break
        return block

    def _process_dependency_file(self, file_path: str):
        """Process dependency files like .csproj, packages.config, packages.lock.json."""
        try:
            if file_path in self.analyzed_files:
                return

            # Security: Check if file is safe to process
            if not self._is_safe_file(file_path):
                return

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(self.max_file_size_bytes)  # Security: Limit read size

            relative_path = os.path.relpath(file_path, self.directory)
            file_node = f"Dependency File: {relative_path}"

            # Add to analyzed files set.
            self.analyzed_files.add(file_path)

            # Add file node if it doesn't exist.
            if not self.graph.has_node(file_node):
                self.graph.add_node(file_node, type="dependency_file", path=relative_path)

            # Process dependencies
            if file_path.endswith(".csproj"):
                # Security: More restrictive regex patterns
                package_pattern = r'<PackageReference\s+Include="([^"<>]{1,100})"\s+Version="([^"<>]{1,50})"\s*/>'
                matches = re.finditer(package_pattern, content)
                for match in matches:
                    package_name = match.group(1)
                    version = match.group(2)
                    
                    # Security: Validate package name format
                    if not re.match(r'^[a-zA-Z0-9\.\-_]+$', package_name):
                        continue
                    
                    dep_node = f"Dependency: {package_name}"
                    if not self.graph.has_node(dep_node):
                        self.graph.add_node(dep_node, type="dependency", name=package_name, version=version)
                    self.graph.add_edge(file_node, dep_node, relation="HAS_DEPENDENCY")

                    self.total_dependencies.add(package_name)
            elif file_path.endswith("packages.config"):
                # Security: More restrictive regex patterns
                package_pattern = r'<package\s+id="([^"<>]{1,100})"\s+version="([^"<>]{1,50})"\s+.*?/>'
                matches = re.finditer(package_pattern, content)
                for match in matches:
                    package_name = match.group(1)
                    version = match.group(2)
                    
                    # Security: Validate package name format
                    if not re.match(r'^[a-zA-Z0-9\.\-_]+$', package_name):
                        continue
                    
                    dep_node = f"Dependency: {package_name}"
                    if not self.graph.has_node(dep_node):
                        self.graph.add_node(dep_node, type="dependency", name=package_name, version=version)
                    self.graph.add_edge(file_node, dep_node, relation="HAS_DEPENDENCY")

                    self.total_dependencies.add(package_name)
            elif file_path.endswith("packages.lock.json"):
                try:
                    data = json.loads(content)
                    dependencies = data.get("dependencies", {})
                    for dep_name, dep_info in dependencies.items():
                        # Security: Validate dependency name
                        if not re.match(r'^[a-zA-Z0-9\.\-_]{1,100}$', str(dep_name)):
                            continue
                            
                        version = dep_info.get("resolved", "")
                        dep_node = f"Dependency: {dep_name}"
                        if not self.graph.has_node(dep_node):
                            self.graph.add_node(dep_node, type="dependency", name=dep_name, version=version)
                        self.graph.add_edge(file_node, dep_node, relation="HAS_LOCKED_DEPENDENCY")

                        self.total_dependencies.add(dep_name)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON in dependency file: {e}", file=sys.stderr)

        except Exception as e:
            # Security: Sanitize error messages
            sanitized_error = self._sanitize_error_message(file_path, str(e))
            print(sanitized_error, file=sys.stderr)

    def save_graph(self, output_path: str):
        """Save the knowledge graph in standard JSON format."""
        try:
            # Security: Validate output path
            output_path = str(pathlib.Path(output_path).resolve())
            
            # Security: Sanitize data before serialization
            sanitized_method_params = self._sanitize_data_for_json(self.method_params)
            sanitized_method_returns = self._sanitize_data_for_json(self.method_returns)
            sanitized_class_methods = self._sanitize_data_for_json(self.class_methods)
            
            # Convert sets to lists for JSON serialization
            metadata = {
                "stats": {
                    "total_files": self.total_files,
                    "total_namespaces": self.total_namespaces,
                    "total_classes": self.total_classes,
                    "total_methods": self.total_methods,
                    "total_interfaces": self.total_interfaces,
                    "total_enums": self.total_enums,
                    "total_structs": self.total_structs,
                    "total_dependencies": len(self.total_dependencies),
                    "total_usings": self.total_usings,
                },
                "method_params": self._convert_sets_to_lists(sanitized_method_params),
                "method_returns": sanitized_method_returns,
                "class_methods": self._convert_sets_to_lists(sanitized_class_methods),
            }

            data = json_graph.node_link_data(self.graph)

            # Security: Safe file writing
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"graph": data, "metadata": metadata}, f, indent=2, ensure_ascii=True)
                
        except Exception as e:
            print(f"Error saving graph: {str(e)}", file=sys.stderr)
            raise
    
    def _sanitize_data_for_json(self, data: Any) -> Any:
        """Sanitize data to prevent JSON injection attacks.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data safe for JSON serialization
        """
        if isinstance(data, dict):
            return {key: self._sanitize_data_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data_for_json(item) for item in data]
        elif isinstance(data, str):
            # Remove any potentially dangerous characters
            sanitized = re.sub(r'[^\w\s\.\-_:,;(){}[\]<>/\\]', '', data)
            return sanitized[:1000]  # Limit length
        else:
            return data

    def _convert_sets_to_lists(self, data_dict):
        """Helper method to convert any sets in a dictionary to lists."""
        for key, value in data_dict.items():
            if isinstance(value, set):
                data_dict[key] = list(value)
            elif isinstance(value, dict):
                data_dict[key] = self._convert_sets_to_lists(value)
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, set):
                        value[idx] = list(item)
                    elif isinstance(item, dict):
                        value[idx] = self._convert_sets_to_lists(item)
        return data_dict

    def visualize_graph(self):
        """Visualize the knowledge graph."""
        try:
            import matplotlib.pyplot as plt

            # Create color map for different node types
            color_map = {
                "file": "#ADD8E6",         # Light blue
                "namespace": "#87CEFA",    # Light sky blue
                "class": "#90EE90",        # Light green
                "interface": "#32CD32",    # Lime green
                "struct": "#20B2AA",       # Light sea green
                "enum": "#FFD700",         # Gold
                "enum_member": "#FFA500",  # Orange
                "method": "#FFE5B4",       # Peach
                "property": "#FFB6C1",     # Light pink
                "event": "#E6E6FA",        # Lavender
                "field": "#DDA0DD",        # Plum
                "dependency_file": "#C0C0C0",  # Silver
                "dependency": "#8A2BE2",   # Blue Violet
            }

            # Set node colors
            node_colors = [
                color_map.get(self.graph.nodes[node].get("type", "file"), "lightgray")
                for node in self.graph.nodes()
            ]

            # Create figure and axis explicitly
            fig, ax = plt.subplots(figsize=(20, 15))

            # Calculate layout
            pos = nx.spring_layout(self.graph, k=1.5, iterations=50)

            # Draw the graph
            nx.draw(
                self.graph,
                pos,
                ax=ax,
                with_labels=True,
                node_color=node_colors,
                node_size=2000,
                font_size=8,
                font_weight="bold",
                arrows=True,
                edge_color="gray",
                arrowsize=20,
            )

            # Add legend
            legend_elements = [
                plt.Line2D(
                    [0], [0],
                    marker='o',
                    color='w',
                    markerfacecolor=color,
                    label=node_type,
                    markersize=10
                )
                for node_type, color in color_map.items()
            ]

            # Place legend outside the plot
            ax.legend(
                handles=legend_elements,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                title="Node Types"
            )

            # Set title
            ax.set_title("C# Code Knowledge Graph Visualization", pad=20)

            # Adjust layout to accommodate legend
            plt.subplots_adjust(right=0.85)

            # Show plot
            plt.show()

        except ImportError:
            print("Matplotlib is required for visualization. Install it using 'pip install matplotlib'.")

    def run(self):
        """Run the analysis and save the graph."""
        try:
            # Analyze the codebase.
            print("\nAnalyzing codebase...")
            self.analyze_codebase()

            # Save in standard format.
            output_file = "cs_code_knowledge_graph.json"
            print("\nSaving graph...")
            self.save_graph(output_file)
            print(f"\nCode knowledge graph saved to {output_file}")

            # Display metadata stats
            print("\nCodebase Statistics:")
            print("-------------------")
            stats = {
                "Total Files": self.total_files,
                "Total Namespaces": self.total_namespaces,
                "Total Classes": self.total_classes,
                "Total Interfaces": self.total_interfaces,
                "Total Structs": self.total_structs,
                "Total Enums": self.total_enums,
                "Total Methods": self.total_methods,
                "Total Usings": self.total_usings,
                "Total Dependencies": len(self.total_dependencies),
            }

            # Calculate max length for padding
            max_len = max(len(key) for key in stats.keys())

            # Print stats in aligned columns
            for key, value in stats.items():
                print(f"{key:<{max_len + 2}}: {value:,}")

            # Optional visualization.
            while True:
                visualize = input("\nWould you like to visualize the graph? (yes/no): ").strip().lower()
                if visualize in ["yes", "no"]:
                    break
                print("Invalid choice. Please enter yes or no.")

            if visualize == "yes":
                print("\nGenerating visualization...")
                self.visualize_graph()

        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"\nError: {str(e)}", file=sys.stderr)
        finally:
            print("\nDone.")


if __name__ == "__main__":
    try:
        # Directory containing the C# codebase.
        print("C# Code Knowledge Graph Generator")
        print("--------------------------------")
        print("Security Notice: This tool will analyze the specified directory.")
        print("Ensure you trust the source code being analyzed.")
        print()
        
        codebase_dir = input("Enter the path to the codebase directory: ").strip()

        # Security: Enhanced validation
        if not codebase_dir:
            raise ValueError("Directory path cannot be empty")

        # Create and analyze the codebase with security limits
        print("\nInitializing with security constraints...")
        print("- Maximum file size: 10MB")
        print("- Maximum files: 10,000")
        print("- Maximum processing time: 1 hour")
        
        ckg = CSCodeKnowledgeGraph(
            directory=codebase_dir,
            max_file_size_mb=10,
            max_files=10000
        )
        ckg.run()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except ValueError as e:
        print(f"\nValidation Error: {str(e)}", file=sys.stderr)
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
    finally:
        print("\nDone.")
