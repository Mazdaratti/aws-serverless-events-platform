############################################
# Primary queue outputs
############################################

output "queue_names" {
  description = "Map of logical queue key to rendered SQS queue name."
  value = merge(
    {
      for queue_key, queue in aws_sqs_queue.primary_with_dlq :
      queue_key => queue.name
    },
    {
      for queue_key, queue in aws_sqs_queue.primary_without_dlq :
      queue_key => queue.name
    }
  )
}

output "queue_arns" {
  description = "Map of logical queue key to rendered SQS queue ARN."
  value = merge(
    {
      for queue_key, queue in aws_sqs_queue.primary_with_dlq :
      queue_key => queue.arn
    },
    {
      for queue_key, queue in aws_sqs_queue.primary_without_dlq :
      queue_key => queue.arn
    }
  )
}

output "queue_urls" {
  description = "Map of logical queue key to rendered SQS queue URL."
  value = merge(
    {
      for queue_key, queue in aws_sqs_queue.primary_with_dlq :
      queue_key => queue.url
    },
    {
      for queue_key, queue in aws_sqs_queue.primary_without_dlq :
      queue_key => queue.url
    }
  )
}

############################################
# Dead-letter queue outputs
############################################

output "dlq_names" {
  description = "Map of logical queue key to rendered DLQ name for queues that create a dedicated DLQ."
  value = {
    for queue_key, queue in aws_sqs_queue.dlq :
    queue_key => queue.name
  }
}

output "dlq_arns" {
  description = "Map of logical queue key to rendered DLQ ARN for queues that create a dedicated DLQ."
  value = {
    for queue_key, queue in aws_sqs_queue.dlq :
    queue_key => queue.arn
  }
}

output "dlq_urls" {
  description = "Map of logical queue key to rendered DLQ URL for queues that create a dedicated DLQ."
  value = {
    for queue_key, queue in aws_sqs_queue.dlq :
    queue_key => queue.url
  }
}
