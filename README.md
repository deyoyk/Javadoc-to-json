# Javadoc to JSON CLI Tool

A command-line Python application that extracts methods and APIs from Javadoc websites and converts them to structured JSON format. This tool is useful for developers, API documenters, and anyone who needs to analyze or repurpose Java API documentation.


## Features

- **Crawls Javadoc websites** to extract all classes and their methods
---

## Sponsor Me

If you find this project useful, consider supporting me:

- [☕ Sponsor me on coff.ee](https://coff.ee/deyoyk)

---

## Talk with Me

Join the community or chat with me directly:

- [💬 Discord server](https://discord.gg/BT7FxVSP)
- **Parses method signatures, parameters, return types, and descriptions**
- **Outputs a comprehensive JSON file** with all discovered APIs
- **Supports pretty-printed or compact JSON output**
- **Handles modern and legacy Javadoc layouts**

---

## Requirements

- Python 3.7+
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python jd_to_json.py <JAVADOC_URL> [options]
```

### Arguments

- `<JAVADOC_URL>`: The base URL of the Javadoc website to parse (e.g., `https://docs.oracle.com/javase/8/docs/api/`)

### Options

- `-o, --output <file>`   Output JSON file (default: prints to stdout)
- `--pretty`              Pretty-print the JSON output
- `-h, --help`            Show help message and exit

### Example

```bash
python jd_to_json.py https://docs.oracle.com/javase/8/docs/api/ -o java8.json --pretty
```

---

## Output Structure

The resulting JSON contains:

- `source_url`: The Javadoc site URL
- `total_classes`: Number of classes found
- `total_methods`: Number of methods found
- `classes`: List of class objects, each with:
  - `name`, `package_name`, `description`, `url`, `type`
  - `methods`: List of method objects, each with:
    - `name`, `return_type`, `parameters`, `description`, `modifiers`, `exceptions`, `class_name`, `package_name`, `url`

---

## Example Output

```json
{
  "source_url": "https://docs.oracle.com/javase/8/docs/api/",
  "total_classes": 2,
  "total_methods": 10,
  "classes": [
    {
      "name": "String",
      "package_name": "java.lang",
      "description": "Class from java.lang",
      "methods": [
        {
          "name": "substring",
          "return_type": "String",
          "parameters": [
            { "name": "beginIndex", "type": "int" },
            { "name": "endIndex", "type": "int" }
          ],
          "description": "Returns a new string that is a substring of this string.",
          "modifiers": ["public"],
          "exceptions": [],
          "class_name": "String",
          "package_name": "java.lang",
          "url": "https://docs.oracle.com/javase/8/docs/api/java/lang/String.html"
        }
      ],
      "url": "https://docs.oracle.com/javase/8/docs/api/java/lang/String.html",
      "type": "class"
    }
  ]
}
```

---

## License

MIT License

---

## Author

- [Deyo]

---

## Contributions

Pull requests and issues are welcome!
