############################################
# Events business table
############################################

# This table stores the canonical event records for the platform.
#
# It owns event metadata plus aggregate RSVP helper counters. Those counters
# improve read efficiency for event responses, but the RSVP table remains the
# source of truth for actual attendance membership.
resource "aws_dynamodb_table" "events" {
  name         = local.events_table_name
  billing_mode = var.billing_mode
  # The current AWS provider line used in this repository still validates the
  # table primary key with hash_key / range_key arguments at the resource root.
  # GSI key definitions are already using the newer key_schema form where the
  # provider accepts it cleanly.
  hash_key    = "event_pk"
  table_class = var.table_class

  attribute {
    name = "event_pk"
    type = "S"
  }

  # These attributes back the public upcoming events index.
  #
  # gsi_pk means "global secondary index partition key".
  # gsi_sk means "global secondary index sort key".
  #
  # This index supports future query-based listing of public upcoming events
  # without relying on a full table scan as the long-term access pattern.
  attribute {
    name = "public_upcoming_gsi_pk"
    type = "S"
  }

  attribute {
    name = "public_upcoming_gsi_sk"
    type = "S"
  }

  # These attributes back the creator events index.
  #
  # This index supports future query-based reads such as "list events created
  # by this user" without adding a speculative RSVP-by-user index in v1.
  attribute {
    name = "creator_events_gsi_pk"
    type = "S"
  }

  attribute {
    name = "creator_events_gsi_sk"
    type = "S"
  }

  # Query path for public event discovery ordered by event date.
  global_secondary_index {
    name = "public-upcoming-events"

    key_schema {
      attribute_name = "public_upcoming_gsi_pk"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "public_upcoming_gsi_sk"
      key_type       = "RANGE"
    }

    projection_type = "ALL"
  }

  # Query path for organizer/creator event listing ordered by event date.
  global_secondary_index {
    name = "creator-events"

    key_schema {
      attribute_name = "creator_events_gsi_pk"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "creator_events_gsi_sk"
      key_type       = "RANGE"
    }

    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery_enabled
  }

  tags = local.events_table_tags
}

############################################
# RSVPs business table
############################################

# This table stores the canonical RSVP membership records for each event.
#
# The base key shape supports efficient per-event reads and keeps the module
# aligned with the synchronous DynamoDB write path chosen for RSVP handling.
resource "aws_dynamodb_table" "rsvps" {
  name         = local.rsvps_table_name
  billing_mode = var.billing_mode
  # The current AWS provider line used in this repository still validates the
  # table primary key with hash_key / range_key arguments at the resource root.
  # GSI key definitions are already using the newer key_schema form where the
  # provider accepts it cleanly.
  hash_key    = "event_pk"
  range_key   = "subject_sk"
  table_class = var.table_class

  attribute {
    name = "event_pk"
    type = "S"
  }

  # subject_sk is the sort key that distinguishes one RSVP subject from
  # another inside the same event partition, for example an authenticated user
  # or an anonymous subject identifier.
  attribute {
    name = "subject_sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery_enabled
  }

  tags = local.rsvps_table_tags
}
