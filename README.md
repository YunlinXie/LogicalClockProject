# Logical Clock Project
This project is based on gRPC Project, the differences are:
1. adding a counter to apply the Lamport's Logical Clock Algorithm.
2. the customer processes (client) run concurrently.
The logical clock functionalities should fulfill the following:
1. The logical clock, C, must always go forward (increasing)
2. If a and b are two events within the same process and a
 occurs before b, then C(a) < C(b)
3.  If a is the sending of a message by one process and b is the reception of that message by another process, then C(a) < C(b)
