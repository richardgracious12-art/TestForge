from flask import Flask, request, jsonify, send_file
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

DATABASE = "testforge.db"


def get_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS requirements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            description TEXT NOT NULL,

            created_date TEXT NOT NULL

        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            requirement_id INTEGER NOT NULL,

            test_case_id TEXT NOT NULL,

            type TEXT NOT NULL,

            scenario TEXT NOT NULL,

            input_value TEXT NOT NULL,

            expected_result TEXT NOT NULL,

            FOREIGN KEY(requirement_id)
            REFERENCES requirements(id)

        )
    """)

    connection.commit()

    connection.close()


# --------------------------------------------------
# FIELD DETECTION
# --------------------------------------------------

def detect_field(text):

    text = text.lower()

    fields = {

        "age": "Age",

        "password": "Password",

        "username": "Username",

        "email": "Email",

        "marks": "Marks",

        "score": "Score",

        "quantity": "Quantity",

        "amount": "Amount",

        "salary": "Salary",

        "price": "Price",

        "phone": "Phone",

        "mobile": "Mobile",

        "name": "Name"

    }

    for key, value in fields.items():

        if key in text:

            return value

    return "Input"


# --------------------------------------------------
# RULE DETECTION
# --------------------------------------------------

def detect_rule(text):

    text = text.lower()


    if re.search(
        r"\bbetween\s+-?\d+(?:\.\d+)?\s+and\s+-?\d+",
        text
    ):

        return "Range"


    if re.search(
        r"\b\d+\s*(?:to|-)\s*\d+\s*(characters?|chars?|digits?)",
        text
    ):

        return "Length"


    if re.search(
        r"\b(at least|minimum(?: of)?|minimum)\s+-?\d+",
        text
    ):

        return "Minimum"


    if re.search(
        r"\b(at most|maximum(?: of)?|maximum)\s+-?\d+",
        text
    ):

        return "Maximum"


    if (
        "required" in text
        or
        "mandatory" in text
    ):

        return "Required"


    if (
        "email" in text
        and
        (
            "valid" in text
            or
            "format" in text
        )
    ):

        return "Format"


    return "General"


# --------------------------------------------------
# NUMBER EXTRACTION
# --------------------------------------------------

def extract_numbers(text):

    return [
        float(number)

        for number in re.findall(
            r"-?\d+(?:\.\d+)?",
            text
        )
    ]


def format_number(number):

    if float(number).is_integer():

        return str(
            int(number)
        )

    return str(number)


# --------------------------------------------------
# REQUIREMENT ANALYSIS
# --------------------------------------------------

def analyze_requirement(text):

    field = detect_field(text)

    rule = detect_rule(text)

    numbers = extract_numbers(text)


    if field in [
        "Age",
        "Marks",
        "Score",
        "Quantity",
        "Amount",
        "Salary",
        "Price"
    ]:

        data_type = "Numeric"


    elif field in [
        "Phone",
        "Mobile"
    ]:

        data_type = "Numeric / String"


    elif field == "Email":

        data_type = "Email"


    else:

        data_type = "Text"


    constraint = "No explicit constraint"


    if (
        rule == "Range"
        and
        len(numbers) >= 2
    ):

        constraint = (
            f"{format_number(numbers[0])}"
            f" to "
            f"{format_number(numbers[1])}"
        )


    elif (
        rule == "Length"
        and
        len(numbers) >= 2
    ):

        constraint = (
            f"{format_number(numbers[0])}"
            f" to "
            f"{format_number(numbers[1])}"
            " characters"
        )


    elif (
        rule == "Minimum"
        and
        numbers
    ):

        constraint = (
            "Minimum "
            +
            format_number(numbers[0])
        )


    elif (
        rule == "Maximum"
        and
        numbers
    ):

        constraint = (
            "Maximum "
            +
            format_number(numbers[0])
        )


    elif rule == "Required":

        constraint = "Value must be provided"


    elif rule == "Format":

        constraint = "Valid format required"


    suggestions = [

        "Test the valid input.",

        "Test invalid input.",

        "Test empty input.",

        "Test boundary values."

    ]


    if rule in [
        "Range",
        "Minimum",
        "Maximum",
        "Length"
    ]:

        suggestions.append(
            "Test values immediately outside the allowed limit."
        )


    if field == "Email":

        suggestions.append(
            "Test malformed email formats."
        )


    if field == "Password":

        suggestions.append(
            "Test weak, short and special-character passwords."
        )


    return {

        "field": field,

        "data_type": data_type,

        "validation": rule,

        "constraint": constraint,

        "suggestions": suggestions

    }


# --------------------------------------------------
# ADD TEST CASE
# --------------------------------------------------

def add_test_case(
    cases,
    test_type,
    scenario,
    input_value,
    expected
):

    cases.append({

        "test_case_id":
            f"TC{len(cases) + 1:03d}",

        "type":
            test_type,

        "scenario":
            scenario,

        "input":
            str(input_value),

        "expected_result":
            expected

    })


# --------------------------------------------------
# GENERATE TEST CASES
# --------------------------------------------------

def generate_test_cases(text):

    field = detect_field(text)

    rule = detect_rule(text)

    numbers = extract_numbers(text)

    cases = []


    # RANGE
    if (
        rule == "Range"
        and
        len(numbers) >= 2
    ):

        minimum = numbers[0]

        maximum = numbers[1]


        add_test_case(
            cases,
            "Positive",
            f"{field} valid value",
            format_number(
                (minimum + maximum) / 2
            ),
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} minimum boundary",
            format_number(minimum),
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} maximum boundary",
            format_number(maximum),
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} below minimum",
            format_number(minimum - 1),
            "Rejected"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} above maximum",
            format_number(maximum + 1),
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} empty input",
            "",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} invalid data type",
            "abc",
            "Rejected"
        )


    # LENGTH
    elif (
        rule == "Length"
        and
        len(numbers) >= 2
    ):

        minimum = int(numbers[0])

        maximum = int(numbers[1])


        add_test_case(
            cases,
            "Positive",
            f"{field} valid length",
            "A" * max(minimum + 1, 1),
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} minimum length",
            "A" * minimum,
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} maximum length",
            "A" * maximum,
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} below minimum length",
            "A" * max(minimum - 1, 0),
            "Rejected"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} above maximum length",
            "A" * (maximum + 1),
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} empty input",
            "",
            "Rejected"
        )


        if field == "Password":

            add_test_case(
                cases,
                "Security",
                "Password with special characters",
                "Aa1!@xyz",
                "Review validation"
            )


    # MINIMUM
    elif (
        rule == "Minimum"
        and
        numbers
    ):

        minimum = numbers[0]


        add_test_case(
            cases,
            "Positive",
            f"{field} above minimum",
            format_number(minimum + 1),
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} minimum boundary",
            format_number(minimum),
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} below minimum",
            format_number(minimum - 1),
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} empty input",
            "",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} invalid data type",
            "abc",
            "Rejected"
        )


    # MAXIMUM
    elif (
        rule == "Maximum"
        and
        numbers
    ):

        maximum = numbers[0]


        add_test_case(
            cases,
            "Positive",
            f"{field} below maximum",
            format_number(maximum - 1),
            "Accepted"
        )


        add_test_case(
            cases,
            "Boundary",
            f"{field} maximum boundary",
            format_number(maximum),
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} above maximum",
            format_number(maximum + 1),
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} empty input",
            "",
            "Rejected"
        )


    # REQUIRED
    elif rule == "Required":

        add_test_case(
            cases,
            "Positive",
            f"{field} provided",
            "Valid value",
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            f"{field} empty",
            "",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} whitespace only",
            "   ",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            f"{field} invalid characters",
            "@@@",
            "Review validation"
        )


    # EMAIL
    elif (
        rule == "Format"
        or
        field == "Email"
    ):

        add_test_case(
            cases,
            "Positive",
            "Valid email format",
            "user@example.com",
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            "Missing @ symbol",
            "userexample.com",
            "Rejected"
        )


        add_test_case(
            cases,
            "Negative",
            "Missing domain",
            "user@",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            "Empty email",
            "",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            "Whitespace email",
            " user@example.com ",
            "Review validation"
        )


    # GENERAL
    else:

        add_test_case(
            cases,
            "Positive",
            "Valid requirement input",
            "Valid value",
            "Accepted"
        )


        add_test_case(
            cases,
            "Negative",
            "Invalid input",
            "Invalid value",
            "Rejected"
        )


        add_test_case(
            cases,
            "Edge",
            "Empty input",
            "",
            "Review validation"
        )


        add_test_case(
            cases,
            "Edge",
            "Whitespace input",
            "   ",
            "Review validation"
        )


    return cases


# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

def calculate_statistics(cases):

    return {

        "total":
            len(cases),

        "positive":
            sum(
                case["type"] == "Positive"
                for case in cases
            ),

        "negative":
            sum(
                case["type"] == "Negative"
                for case in cases
            ),

        "boundary_edge":
            sum(
                case["type"] in
                ["Boundary", "Edge"]
                for case in cases
            )

    }


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    return send_file(
        "index.html"
    )


# --------------------------------------------------
# GENERATE API
# --------------------------------------------------

@app.route(
    "/generate",
    methods=["POST"]
)
def generate():

    data =request.get_json(silent=True) or {}


    requirement =str(data.get("requirement","")).strip()

    if not requirement:

        return jsonify({

            "error":
                "Requirement cannot be empty."

        }), 400


    cases =generate_test_cases(requirement)


    analysis =analyze_requirement(requirement)


    statistics =calculate_statistics(cases)


    return jsonify({

        "field":
            analysis["field"],

        "rule":
            analysis["validation"],

        "analysis":
            analysis,

        "stats":
            statistics,

        "test_cases":
            cases

    })


# --------------------------------------------------
# SAVE API
# --------------------------------------------------

@app.route(
    "/save",
    methods=["POST"]
)
def save():

    data =request.get_json(silent=True) or {}


    requirement =str(data.get("requirement","")).strip()


    if not requirement:

        return jsonify({

            "error":
                "Requirement cannot be empty."

        }), 400


    cases =generate_test_cases(requirement)


    connection =get_connection()


    cursor =connection.cursor()


    created_date =datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    cursor.execute(
        """
        INSERT INTO requirements
        (
            description,
            created_date
        )

        VALUES (?, ?)
        """,

        (
            requirement,
            created_date
        )
    )


    requirement_id =cursor.lastrowid


    for case in cases:

        cursor.execute(
            """
            INSERT INTO test_cases
            (
                requirement_id,
                test_case_id,
                type,
                scenario,
                input_value,
                expected_result
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,

            (
                requirement_id,

                case["test_case_id"],

                case["type"],

                case["scenario"],

                case["input"],

                case["expected_result"]
            )
        )


    connection.commit()

    connection.close()


    return jsonify({

        "message":
            "Requirement and test cases saved successfully."

    })


# --------------------------------------------------
# HISTORY API
# --------------------------------------------------

@app.route("/history")
def history():

    connection =get_connection()


    requirements =connection.execute(
            """
            SELECT
                id,
                description,
                created_date

            FROM requirements

            ORDER BY id DESC
            """
        ).fetchall()


    result = []


    for requirement in requirements:

        rows =connection.execute(
                """
                SELECT

                    test_case_id,

                    type,

                    scenario,

                    input_value,

                    expected_result

                FROM test_cases

                WHERE requirement_id = ?

                ORDER BY id
                """,

                (
                    requirement["id"],
                )
            ).fetchall()


        test_cases = []


        for row in rows:

            test_cases.append({

                "test_case_id":
                    row["test_case_id"],

                "type":
                    row["type"],

                "scenario":
                    row["scenario"],

                "input":
                    row["input_value"],

                "expected_result":
                    row["expected_result"]

            })


        result.append({

            "id":
                requirement["id"],

            "description":
                requirement["description"],

            "created_date":
                requirement["created_date"],

            "test_cases":
                test_cases

        })


    connection.close()


    return jsonify(result)


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    init_database()

    app.run(
        debug=True
    )