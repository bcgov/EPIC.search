from marshmallow import Schema, fields, EXCLUDE

class StatsRequestSchema(Schema):
    """Schema for stats API request validation.
    Used for POST /stats/processing to filter by project IDs.
    """
    class Meta:
        unknown = EXCLUDE

    projectIds = fields.List(
        fields.Str(),
        data_key="projectIds",
        required=False,
        allow_none=True,
        metadata={"description": "Optional list of project IDs to filter stats. If not provided, returns stats for all projects."}
    )

class ProjectStatsSchema(Schema):
    project_id = fields.Str()
    project_name = fields.Str()
    total_files = fields.Int()
    successful_files = fields.Int()
    failed_files = fields.Int()
    skipped_files = fields.Int()
    success_rate = fields.Float()

class ProcessingStatsSummarySchema(Schema):
    total_projects = fields.Int()
    total_files_across_all_projects = fields.Int()
    total_successful_files = fields.Int()
    total_failed_files = fields.Int()
    total_skipped_files = fields.Int()
    overall_success_rate = fields.Float()
    projects_with_failures = fields.Int(required=False)
    avg_success_rate_per_project = fields.Float(required=False)

class ProcessingStatsSchema(Schema):
    projects = fields.List(fields.Nested(ProjectStatsSchema))
    summary = fields.Nested(ProcessingStatsSummarySchema)

class ProcessingLogMetricsSchema(Schema):
    processing_time_ms = fields.Int()
    file_size_bytes = fields.Int()

class ProcessingLogSchema(Schema):
    log_id = fields.Int()
    document_id = fields.Str()
    status = fields.Str()
    processed_at = fields.DateTime()
    metrics = fields.Nested(ProcessingLogMetricsSchema)

class ProjectDetailsSummarySchema(Schema):
    total_files = fields.Int()
    successful_files = fields.Int()
    failed_files = fields.Int()
    skipped_files = fields.Int()
    success_rate = fields.Float()

class ProjectDetailsSchema(Schema):
    project_id = fields.Str()
    project_name = fields.Str()
    processing_logs = fields.List(fields.Nested(ProcessingLogSchema))
    summary = fields.Nested(ProjectDetailsSummarySchema)

class ProcessingSummarySchema(Schema):
    total_projects = fields.Int()
    total_files_across_all_projects = fields.Int()
    total_successful_files = fields.Int()
    total_failed_files = fields.Int()
    total_skipped_files = fields.Int()
    overall_success_rate = fields.Float()
    projects_with_failures = fields.Int()
    avg_success_rate_per_project = fields.Float()
