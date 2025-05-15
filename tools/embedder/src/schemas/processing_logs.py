from marshmallow import Schema, fields

"""
Processing Logs Schema module.

This module defines the data schema for serializing and deserializing
ProcessingLog objects, using the Marshmallow library for validation
and data transformation.
"""

class ProcessingLogSchema(Schema):
    """
    Marshmallow schema for the ProcessingLog model.
    
    This schema defines how ProcessingLog instances are serialized to and 
    deserialized from JSON, including field validation and transformation.
    
    Attributes:
        id (Int): The unique identifier for the processing log entry (output only)
        project_id (Str): The identifier of the project the document belongs to
        document_id (Str): The identifier of the document that was processed
        status (Str): The status of the processing operation (success or failure)
        processed_at (DateTime): The timestamp when the document was processed (output only)
    """
    id = fields.Int(dump_only=True)
    project_id = fields.Str(required=True)
    document_id = fields.Str(required=True)
    status = fields.Str(required=True)
    processed_at = fields.DateTime(dump_only=True)