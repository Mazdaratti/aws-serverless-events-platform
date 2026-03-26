############################################
# Normalized queue configuration
############################################

locals {
  # These defaults keep the v1 module small and predictable while still making
  # the caller's queue definitions less repetitive.
  queue_defaults = {
    create_dlq                 = false
    visibility_timeout_seconds = 30
    message_retention_seconds  = 345600
    receive_wait_time_seconds  = 0
    max_receive_count          = null
  }

  # Normalize the caller input once so the rest of the module can work with a
  # fully-populated and consistent queue map.
  normalized_queues = {
    for queue_key, queue in var.queues :
    queue_key => merge(local.queue_defaults, queue)
  }

  # Render the final queue names from the shared prefix plus the logical key.
  rendered_queue_names = {
    for queue_key in keys(local.normalized_queues) :
    queue_key => "${var.name_prefix}-${queue_key}"
  }

  rendered_dlq_names = {
    for queue_key, queue in local.normalized_queues :
    queue_key => "${local.rendered_queue_names[queue_key]}-dlq"
    if queue.create_dlq
  }

  # Split queues by DLQ behavior so resource blocks can stay simple and avoid
  # repeating conditional filtering logic.
  queues_with_dlq = {
    for queue_key, queue in local.normalized_queues :
    queue_key => queue
    if queue.create_dlq
  }

  queues_without_dlq = {
    for queue_key, queue in local.normalized_queues :
    queue_key => queue
    if !queue.create_dlq
  }
}
