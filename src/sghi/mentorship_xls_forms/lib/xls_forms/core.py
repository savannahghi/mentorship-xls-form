from collections.abc import Sequence
from typing import Literal, Self

from attrs import define, field

from sghi.utils import ensure_not_none, ensure_not_none_nor_empty

# =============================================================================
# TYPES
# =============================================================================

XLSFormBoolean = Literal["yes", "no"]

XLSFormElementType = Literal[
    "acknowledge",  # Acknowledge prompt that sets value to "OK" if selected.
    "audio",  # Take an audio recording or upload an audio file.
    "background-audio",  # Audio is recorded in the background while filling the form.  # noqa: E501
    "barcode",  # Scan a barcode, requires the barcode scanner app to be installed.  # noqa: E501
    "begin_group",  # Start a new group.
    "calculate",  # Perform a calculation; see the Calculation section below.
    "date",  # Date input.
    "dateTime",  # Accepts a date and a time input.
    "decimal",  # Decimal input.
    "end_group",  # Marks the end of a group.
    "file",  # Generic file input (txt, pdf, xls, xlsx, doc, docx, rtf, zip)
    "geopoint",  # Collect a single GPS coordinate.
    "geoshape",  # Record a polygon of multiple GPS coordinates; the last point is the same as the first point.  # noqa: E501
    "geotrace",  # Record a line of two or more GPS coordinates.
    "hidden",  # A field with no associated UI element which can be used to store a constant.  # noqa: E501
    "image",  # Take a picture or upload an image file.
    "integer",  # Integer (i.e., whole number) input.
    "note",  # Display a note on the screen, takes no input. Shorthand for type=text with readonly=true.  # noqa: E501
    "range",  # Range input (including rating)
    "rank [options]",  # Rank question; order a list.
    "select_one [options]",  # Multiple choice question; only one answer can be selected.  # noqa: E501
    "select_multiple [options]",  # Multiple choice question; multiple answers can be selected.  # noqa: E501
    "select_one_from_file [file]",  # Multiple choice from file; only one answer can be selected.  # noqa: E501
    "select_multiple_from_file [file]",  # Multiple choice from file; multiple answers can be selected.  # noqa: E501
    "text",  # Free text response.
    "time",  # Time input.
    "trigger",  # Ok?
    "video",  # Take a video recording or upload a video file.
    "xml-external",  # Adds a reference to an external XML data file
]


# =============================================================================
# XLSForm Domain Items
# =============================================================================


@define
class XLSFormChoice:
    label: str = field()
    list_name: str = field()
    name: str = field()
    county: str | None = field(default=None, repr=False)
    sub_county: str | None = field(default=None, repr=False)
    ward: str | None = field(default=None, repr=False)


@define
class XLSFormRecord:
    type: XLSFormElementType = field()
    appearance: str | None = field(default=None, kw_only=True, repr=False)
    calculation: str | None = field(default=None, kw_only=True, repr=False)
    choice_filter: str | None = field(default=None, kw_only=True, repr=False)
    constraint: str | None = field(default=None, kw_only=True, repr=False)
    constraint_message: str | None = field(
        default=None,
        kw_only=True,
        repr=False,
    )
    default: str | None = field(default=None, kw_only=True, repr=False)
    hint: str | None = field(default=None, kw_only=True, repr=False)
    label: str | None = field(default=None, kw_only=True)
    name: str | None = field(default=None, kw_only=True)
    note: str | None = field(default=None, kw_only=True, repr=False)
    repeat_count: int | str | None = field(
        default=None,
        kw_only=True,
        repr=False,
    )
    parameters: str | None = field(default=None, kw_only=True, repr=False)
    read_only: XLSFormBoolean | None = field(default=None, kw_only=True)
    relevant: str | None = field(default=None, kw_only=True, repr=False)
    required: XLSFormBoolean | None = field(
        default=None,
        kw_only=True,
        repr=False,
    )
    required_message: str | None = field(
        default=None,
        kw_only=True,
        repr=False,
    )
    trigger: str | None = field(default=None, kw_only=True)

    @classmethod
    def begin_group(
        cls,
        appearance: str | None = None,
        hint: str | None = None,
        label: str | None = None,
        name: str | None = None,
        relevant: str | None = None,
    ) -> Self:
        return cls(
            type="begin_group",
            appearance=appearance,
            hint=hint,
            label=label,
            name=name,
            relevant=relevant,
        )

    @classmethod
    def begin_field_list(
        cls,
        label: str | None = None,
        name: str | None = None,
        relevant: str | None = None,
    ) -> Self:
        return cls.begin_group(
            appearance="field-list",
            label=label,
            name=name,
            relevant=relevant,
        )

    @classmethod
    def end_group(cls) -> Self:
        return cls(type="end_group")

    @classmethod
    def of_note(
        cls,
        label: str | None,
        name: str | None = None,
        calculation: str | None = None,
        hint: str | None = None,
        relevant: str | None = None,
    ) -> Self:
        return cls(
            type="note",
            label=label,
            name=name,
            calculation=calculation,
            hint=hint,
            relevant=relevant,
        )

    @classmethod
    def of_positive_integer(
        cls,
        calculation: str | None = None,
        constraint_message: str | None = "This value must be >= 0",
        default: int | None = None,
        hint: str | None = None,
        name: str | None = None,
        label: str | None = None,
        read_only: XLSFormBoolean | None = None,
        relevant: str | None = None,
    ) -> Self:
        return cls(
            type="integer",
            calculation=calculation,
            constraint=".>=0",
            constraint_message=constraint_message,
            default=None if default is None else str(default),
            hint=hint,
            name=name,
            label=label,
            read_only=read_only,
            relevant=relevant,
        )

    @classmethod
    def of_select_multiple(
        cls,
        list_name: str,
        appearance: str | None = None,
        hint: str | None = None,
        label: str | None = None,
        name: str | None = None,
        relevant: str | None = None,
        required: XLSFormBoolean | None = None,
    ) -> Self:
        required_msg: str = "'list_name' MUST not be None or empty."
        ensure_not_none_nor_empty(list_name, required_msg)
        return cls(
            type=f"select_multiple {list_name}",  # type: ignore
            appearance=appearance,
            hint=hint,
            label=label,
            name=name,
            relevant=relevant,
            required=required,
        )

    @classmethod
    def of_select_one(
        cls,
        list_name: str,
        appearance: str | None = None,
        calculation: str | None = None,
        choice_filter: str | None = None,
        default: str | None = None,
        hint: str | None = None,
        label: str | None = None,
        name: str | None = None,
        read_only: XLSFormBoolean | None = None,
        relevant: str | None = None,
        required: XLSFormBoolean | None = None,
    ) -> Self:
        required_msg: str = "'list_name' MUST not be None or empty."
        ensure_not_none_nor_empty(list_name, required_msg)
        return cls(
            type=f"select_one {list_name}",  # type: ignore
            appearance=appearance,
            calculation=calculation,
            choice_filter=choice_filter,
            default=default,
            hint=hint,
            label=label,
            name=name,
            read_only=read_only,
            relevant=relevant,
            required=required,
        )

    @classmethod
    def of_trigger(
        cls,
        appearance: str = "horizontal",
        hint: str | None = None,
        name: str | None = None,
        label: str | None = "Not Applicable?",
    ) -> Self:
        return cls(
            type="trigger",
            appearance=appearance,
            name=name,
            label=label,
            hint=hint,
        )


@define
class XLSFormItem:
    records: Sequence[XLSFormRecord] = field(repr=False)
    choices: Sequence[XLSFormChoice] = field(factory=tuple, repr=False)

    @classmethod
    def of_records(cls, records: Sequence[XLSFormRecord]) -> Self:
        ensure_not_none_nor_empty(
            value=records,
            message="'records' MUST not be None or empty.",
        )
        return cls(records=records)

    @classmethod
    def of_single_record(cls, record: XLSFormRecord) -> Self:
        ensure_not_none(record, "'record' MUST not be None.")
        return cls.of_records(records=(record,))


@define
class XLSFormSettings:
    form_id: str = field()
    form_title: str = field()
    default_language: str | None = field(
        default="English (en)",
        kw_only=True,
        repr=False,
    )
    instance_name: str | None = field(default=None, kw_only=True, repr=False)
    style: str | None = field(default="pages", kw_only=True, repr=False)
    version: str | None = field(default="1.5.0", kw_only=True)


@define
class XLSForm:
    survey: Sequence[XLSFormRecord] = field(repr=False)
    choices: Sequence[XLSFormChoice] = field(repr=False)
    settings: XLSFormSettings = field()
