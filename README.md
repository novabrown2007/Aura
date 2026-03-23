# Aura Assistant

**Author:** Nova Brown
**Copyright:** © Nova Brown — All Rights Reserved

---

## Overview

Aura is a modular personal assistant framework designed to provide intelligent automation, conversational interaction, and extensible system control.

The project is structured around a modular architecture that separates core systems such as runtime management, threading, routing, language model interaction, and interface handling. This design allows Aura to be expanded with additional modules while maintaining a stable and maintainable core.

Aura is currently under active development and its internal architecture may evolve as new features and improvements are implemented.

---

## Version

**Current Version:** Development Build

Aura is currently in an early development stage. The architecture and internal systems are still being refined, and future updates may introduce structural changes, new modules, or expanded capabilities.

Version numbers will be assigned once the project reaches a stable milestone.

---

## Project Structure

The project is organized into several major subsystems:

* **Core Runtime**

  * Runtime context and system lifecycle management

* **Threading System**

  * Task management
  * Event system
  * Background scheduling

* **Routing System**

  * Input interpretation
  * Intent routing
  * Module handling

* **LLM Integration**

  * Language model interaction
  * Conversation history management
  * Long-term memory handling

* **Interface Layer**

  * Input and output management
  * Future support for voice, web, and mobile interfaces

* **Module System**

  * Extensible plugin-style architecture for adding assistant capabilities

---

## Development Status

Aura is currently being developed as a personal research and development project.
Features, architecture, and interfaces may change significantly between revisions.

---

## License and Usage Restrictions

This software and all associated source code are the exclusive intellectual property of **Nova Brown**.

**All rights are reserved.**

The contents of this repository may **not** be:

* shared
* redistributed
* copied
* modified
* published
* or used in derivative works

without explicit written permission from the author.

This project is intended for **private development and experimentation only**.

Unauthorized distribution or reproduction of any part of this software is strictly prohibited.

---

## Contact

Project maintained by **Nova Brown**.

---

## Testing

Run all tests:

```bash
python run_tests.py
```

Run individual suites:

```bash
python run_tests.py --suite build
python run_tests.py --suite command_registry
python run_tests.py --suite runtime_smoke
python run_tests.py --suite short_memory
python run_tests.py --suite long_memory
python run_tests.py --suite system_commands
python run_tests.py --suite llm
python run_tests.py --suite mysql_integration
```

Optional live LLM connectivity test:

```bash
$env:RUN_LIVE_LLM_TEST="true"
$env:LLM_ENDPOINT="http://localhost:11434/api/generate"
$env:LLM_MODEL="llama3.1:8b"
python run_tests.py --suite llm
```

Optional live MySQL integration test:

```bash
$env:RUN_LIVE_MYSQL_TEST="true"
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_NAME="aura"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
python run_tests.py --suite mysql_integration
```
