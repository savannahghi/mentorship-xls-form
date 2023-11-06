# Mentorship Tools as XLSForms

A tool used to generate [XLSForms](https://xlsform.org/en/) for the Mentorship
Checklist tools. The generated XLSForms can then be loaded to any
[ODK ecosystem](https://getodk.github.io/xforms-spec/) tools and used to
undertake the mentorship.

## Usage

Clone the project and run the following command to install the application, and
its dependencies:

```bash
pip install -e .[dev,test,docs]
```

Run the following command on your terminal from the root directory of the
project to use the tool.

```bash
mentorship-xls-forms "resources/Mentorship Checklist Metadata v1.0.0.xlsx" resources/facilities.json
```

The generated XLSForms can be found on the `out` directory.
