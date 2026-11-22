# Task queue notes

The in-process queue loses tasks when the API restarts, and it cannot run jobs
on a second machine. We want a persistent queue with retries. The team has not
chosen a library or a broker yet; there is no Redis or RabbitMQ in our stack.
