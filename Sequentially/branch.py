import grpc
import json
import banks_pb2
import banks_pb2_grpc

class Branch(banks_pb2_grpc.BankServicer):

    def __init__(self, id, balance, branches):
        # Initialize branch ID, balance, and list of branch IDs for communication
        self.id = id
        self.balance = balance
        self.branches = branches
        self.stubList = list()
        self.branches_except_self = list()
        self.logical_clock = 0
        self.branch_events_log = list()

        # Create gRPC stubs to communicate with other branches
        for branch_id in self.branches:
            if branch_id != self.id:
                self.branches_except_self.append(branch_id)
                branch_channel = grpc.insecure_channel(f'localhost:{50050 + branch_id}')
                self.stubList.append(banks_pb2_grpc.BankStub(branch_channel))

    def GetBranchEventsLog(self, request, context):
        print(f"Branch {self.id} current branch_events_log: {self.branch_events_log}")
        events_as_strings = [json.dumps(event) for event in self.branch_events_log]
        return banks_pb2.BranchEventsLogResponse(events=events_as_strings)


    def MsgDelivery(self, request, context):
        self.logical_clock = max(self.logical_clock, request.logical_clock) + 1

        if request.operation == "deposit":
            self.branch_events_log.append({
                "customer-request-id": request.customer_request_id,
                "logical_clock": self.logical_clock,
                "interface": "deposit",
                "comment": f"event_recv from customer {request.customer_id}"
            })
            return self.Deposit(request, context)

        elif request.operation == "withdraw":
            self.branch_events_log.append({
                "customer-request-id": request.customer_request_id,
                "logical_clock": self.logical_clock,
                "interface": "withdraw",
                "comment": f"event_recv from customer {request.customer_id}"
            })
            return self.Withdraw(request, context)

        elif request.operation == "propagate_deposit":
            self.branch_events_log.append({
                "customer-request-id": request.customer_request_id,
                "logical_clock": self.logical_clock,
                "interface": "propagate_deposit",
                "comment": f"event_recv from branch {request.branch_id}"
            })
            return self.Propagate_Deposit(request, context)

        elif request.operation == "propagate_withdraw":
            self.branch_events_log.append({
                "customer-request-id": request.customer_request_id,
                "logical_clock": self.logical_clock,
                "interface": "propagate_withdraw",
                "comment": f"event_recv from branch {request.branch_id}"
            })
            return self.Propagate_Withdraw(request, context)

        elif request.operation == "query":
            return self.Query(request, context)

    def Deposit(self, request, context):
        self.balance += request.amount
        # print(f"Customer {request.customer_id} deposited {request.amount} to Branch {self.id}. New balance: {self.balance}")
        
        # Propagate the deposit to other branches
        for i in range(len(self.branches_except_self)):
            self.logical_clock += 1
            self.branch_events_log.append({
                "customer-request-id": request.customer_request_id,
                "logical_clock": self.logical_clock,
                "interface": "propagate_deposit",
                "comment": f"event_sent to branch {self.branches_except_self[i]}"
            })

            self.stubList[i].MsgDelivery(banks_pb2.TransactionRequest(
                customer_id = request.customer_id,
                customer_request_id = request.customer_request_id,
                operation = "propagate_deposit",
                logical_clock = self.logical_clock,
                branch_id = self.id,
                amount = request.amount
            ))

        return banks_pb2.TransactionResponse(status="success")


    def Withdraw(self, request, context):
        if request.amount <= self.balance:
            self.balance -= request.amount
            # print(f"Customer {request.customer_id} withdrew {request.amount} from Branch {self.id}. New balance: {self.balance}")

            # Propagate the withdrawal to other branches
            for i in range(len(self.branches_except_self)):
                self.logical_clock += 1
                self.branch_events_log.append({
                    "customer-request-id": request.customer_request_id,
                    "logical_clock": self.logical_clock,
                    "interface": "propagate_withdraw",
                    "comment": f"event_sent to branch {self.branches_except_self[i]}"
                })

                self.stubList[i].MsgDelivery(banks_pb2.TransactionRequest(
                    customer_id = request.customer_id,
                    customer_request_id = request.customer_request_id,
                    operation = "propagate_withdraw",
                    logical_clock = self.logical_clock,
                    branch_id = self.id,
                    amount = request.amount
                ))
            return banks_pb2.TransactionResponse(status="success")
        else:
            # Insufficient funds
            return banks_pb2.TransactionResponse(status="fail")

    def Query(self, request, context):
        # print(f"Customer {request.customer_id} queried balance from Branch {self.id}. Balance: {self.balance}")
        return banks_pb2.TransactionResponse(status="success", balance=self.balance)

    def Propagate_Deposit(self, request, context):
        self.balance += request.amount
        # print(f"Branch {self.id} received a propagated deposit of {request.amount}. New balance: {self.balance}")
        return banks_pb2.TransactionResponse(status="success")

    # Inter-branch propagation of withdrawal
    def Propagate_Withdraw(self, request, context):
        if request.amount <= self.balance:
            self.balance -= request.amount
            # print(f"Branch {self.id} received a propagated withdrawal of {request.amount}. New balance: {self.balance}")
            return banks_pb2.TransactionResponse(status="success")
        else:
            print(f"Branch {self.id} failed to apply a propagated withdrawal of {request.amount}. Insufficient funds.")
            return banks_pb2.TransactionResponse(status="fail")