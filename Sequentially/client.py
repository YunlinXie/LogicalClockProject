import grpc
import json
import sys
import multiprocessing
import customer
import time
from banks_pb2_grpc import BankStub
from banks_pb2 import BranchEventsLogRequest

def start_customer_process(customer_id, requests):
    # Initialize Customer, create stub, and execute events
    cust = customer.Customer(customer_id, requests)
    cust.createStub()
    cust.executeEvents()
    return {"id": customer_id, "type": "customer", "events": cust.customer_events_log}

def collect_branch_logs(branch_ids):
    # Collect logs from all branches via gRPC
    all_branches_logs = []
    for branch_id in branch_ids:
        try:
            port = 50050 + branch_id  # Match the branch port
            channel = grpc.insecure_channel(f'localhost:{50050 + branch_id}')
            stub = BankStub(channel)
            response = stub.GetBranchEventsLog(BranchEventsLogRequest())
            # Decode JSON strings back to dictionaries
            branch_logs = [json.loads(event) for event in response.events]
            # Sort the logs by the "logical_clock" attribute
            sorted_branch_logs = sorted(branch_logs, key=lambda x: x["logical_clock"])
            all_branches_logs.append({"id": branch_id, "type": "branch", "events": sorted_branch_logs})
        except grpc.RpcError as e:
            print(f"Failed to fetch logs from branch {branch_id}: {e}")
    return all_branches_logs


def extract_events(logs, log_type):
    events = []
    for log in logs:
        for event in log["events"]:
            events.append({
                "id": log["id"],
                "customer-request-id": event.get("customer-request-id"),
                "type": log_type,
                "logical_clock": event.get("logical_clock"),
                "interface": event.get("interface"),
                "comment": event.get("comment")
            })
    return events


def main():
    # Load the customer configurations from the input JSON file
    with open(sys.argv[1]) as f:
        config = json.load(f)

    # Filter customer elements from the configuration
    customers = [item for item in config if item['type'] == 'customer']
    branches = [item for item in config if item['type'] == 'branch']
    branch_ids = [branch['id'] for branch in branches]
    all_logs = []

    # Start each customer process sequentially with a delay to allow propagation
    all_customers_logs = []
    for cust in customers:
        result = start_customer_process(cust['id'], cust['customer-requests'])
        all_customers_logs.append(result)
        time.sleep(3)  # Delay for propagation

    all_branches_logs = collect_branch_logs(branch_ids)
    all_events = extract_events(all_customers_logs, "customer") + extract_events(all_branches_logs, "branch")
    all_events.sort(key=lambda x: (x["customer-request-id"], x["logical_clock"]))
    all_logs = all_customers_logs + all_branches_logs + all_events

    # Write the output data to output.json file in the current directory
    with open("output.json", "w") as outfile:
        json.dump(all_logs, outfile, indent=4)

if __name__ == '__main__':
    main()