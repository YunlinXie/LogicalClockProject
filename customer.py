import grpc
import banks_pb2
import banks_pb2_grpc

class Customer:
    def __init__(self, id, requests):
        # Initialize customer with ID and list of events to perform
        self.id = id
        self.requests = requests
        self.customer_events_log = list() # Store responses from branch
        self.stub = None # gRPC stub to communicate with branch
        self.logical_clock = 0

    def createStub(self):
        # Connect to the branch with the corresponding customer ID on port 50050 + id
        branch_address = f'localhost:{50050 + self.id}'
        channel = grpc.insecure_channel(branch_address)
        self.stub = banks_pb2_grpc.BankStub(channel)
   
    def executeEvents(self):
        for request in self.requests:
            self.logical_clock += 1
            self.customer_events_log.append({
                "customer-request-id": request["customer-request-id"],
                "logical_clock": self.logical_clock,
                "interface": request["interface"],
                "comment": f"event_sent from customer {self.id}"
            })

            if request["interface"] == "deposit":
                # Send a deposit request to the branch server
                response = self.stub.MsgDelivery(
                    banks_pb2.TransactionRequest(
                        customer_id = self.id,
                        customer_request_id = request["customer-request-id"],
                        operation = "deposit",
                        logical_clock = self.logical_clock,
                        amount = request["money"]
                    )
                )
            elif request["interface"] == "withdraw":
                # Send a withdraw request to the branch server
                response = self.stub.MsgDelivery(
                    banks_pb2.TransactionRequest(
                        customer_id = self.id,
                        customer_request_id = request["customer-request-id"],
                        operation = "withdraw",
                        logical_clock = self.logical_clock,
                        amount = request["money"]
                    )
                )
            elif request["interface"] == "query": # didn't modified this, because query requests don't apply for this project
                response = self.stub.MsgDelivery(
                    banks_pb2.TransactionRequest(
                        customer_id=self.id,
                        operation="query"
                    )
                )
        print(f"Customer {self.id} received messages: {self.customer_events_log}")