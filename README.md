# LeetPeek
LeetPeek is a tool that fetches all the relevant interview experiences or compensation details of a company from leetcode

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python leetpeek.py --company <company_name>
```

## Example
```bash
python leetpeek.py --company google
```

## Output
The output will be saved in the `articles/<company_name>` directory.

## Advanced Usage
```bash
python leetpeek.py --company <company_name> --thresh <threshold>
python leetpeek.py --company <company_name> --type <type>
```

#### Threshold
The threshold is the minimum number of characters in the interview experience. Default is 500.

#### Type
The type can be either `interview` or `compensation`. Default is `interview`.
