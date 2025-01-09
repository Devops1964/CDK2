import json

# Load the outputs from the JSON file
with open("stack_outputs.json", "r") as file:
    data = json.load(file)

# Extract the desired outputs
output_dict = {entry["OutputKey"]: entry["OutputValue"] for entry in data}

# Save in a simplified JSON format
with open("formatted_outputs.json", "w") as file:
    json.dump(output_dict, file, indent=4)

print("Formatted outputs saved to 'formatted_outputs.json'")
