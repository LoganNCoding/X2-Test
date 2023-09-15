import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel
import os, shutil
import re
import concurrent.futures
import wmi 
import calendar
from datetime import datetime, timedelta

# Create the main window
root = tk.Tk()
root.title("X2 Search")

# Function to populate the USB drive list with drive names and letters
def populate_usb_drives():
    # Initialize a WMI connection
    c = wmi.WMI()
    # Query for USB disk drives
    usb_devices = c.Win32_DiskDrive(InterfaceType="USB")
    usb_drives = []
    for device in usb_devices:
        if device.MediaType == "Removable Media":
            drive_name = device.Caption
            drive_letter = None
            # Try to get the drive letter from the partitions
            for partition in device.associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                    drive_letter = logical_disk.DeviceID
                    break
                if drive_letter:
                    break
            usb_drive_info = f"({drive_letter}) {drive_name}"
            usb_drives.append(usb_drive_info)
    return usb_drives

# Function to search for the file
def search_file(root_dir, file_name):
    for root, dirs, files in os.walk(root_dir):
        if file_name in files:
            return os.path.join(root, file_name)
    return None

# Define the name of the file you want to find on the USB drive
file_names_to_find = ['version.json', 'USBSEL.lct']

# Define the specific text pattern for MCU and FW version
text_patterns = {
    'version.json': [
        r'"BWC Firmware":\s*"([^"]*)"',  # Look for BWC FW
        r'"MCU Firmware":\s*"([^"]*)"',  # Look for MCU FW
    ],
}

# Set the width and height of the window
window_width = 900  # Modify the width as needed
window_height = 600  # Modify the height as needed
root.geometry(f"{window_width}x{window_height}")

def update_calendar():
    selected_drive_info = usb_drive_combobox.get()  # Get the selected USB drive info
    print(selected_drive_info)
    if not selected_drive_info:
        return  # No drive selected

    # Extract the drive letter from the selected drive info
    drive_letter = selected_drive_info.split(" ")[0].strip("()")
    print(drive_letter)
    
    # Construct the USB drive root path
    usb_drive_root = f"{drive_letter}\\"
    print(usb_drive_root)
    # Function to print messages to the result_text_widget
    def print_to_text_widget(message):
        result_text_widget.insert(tk.END, message + "\n")
        result_text_widget.see(tk.END)  # Scroll to the end
    selected_date = calendar_widget.get_date()
    year = selected_date.year
    month = selected_date.month
    day = selected_date.day

    new_date = calendar.datetime.datetime(year, month, day)
    calendar_widget.set_date(new_date)

    # Format the date and month with leading zeros
    month = f"{month:02}"
    day = f"{day:02}"
    # Function to print messages to the result_text_widget
    def print_to_text_widget(message):
        result_text_widget.insert(tk.END, message + "\n")
        result_text_widget.see(tk.END)  # Scroll to the end
    hour = hour_entry.get()
    minute = minute_entry.get()
    if not hour or not minute:
        messagebox.showinfo("Information", "Please choose the time.")
    else:
        print_to_text_widget(f'On {year}/{month}/{day}')

    # Generate the filename based on the chosen date, month, and year
    def generate_filename(year, month, day):
        return f"{year}{month}{day}.log"
    
    # Generate the filename
    filename = generate_filename(year, month, day)
    print(filename)

    # Check if the file exists
    def file_exists(filename):
        return os.path.exists(filename)

    # Read the content of the file
    def read_file_content(filename):
        with open(filename, 'r') as file:
            content = file.read()
            return content
    
    # Function to search for the nearest timestamp with 100% SOC
    def find_nearest_timestamp(log_content, target_time):
        timestamp_pattern = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}"
        all_timestamps = re.findall(timestamp_pattern, log_content)
        target_datetime = datetime.strptime(f"{year}/{month}/{day} {target_time}", "%Y/%m/%d %H:%M")
        nearest_timestamp = None
        nearest_time_difference = timedelta.max

        for timestamp_str in all_timestamps:
            timestamp_datetime = datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S")
            time_difference = abs(target_datetime - timestamp_datetime)

            if f"{timestamp_str}, Gauge Info,StateOfCharge=100%" in log_content:
                if time_difference < nearest_time_difference:
                    nearest_timestamp = timestamp_str
                    nearest_time_difference = time_difference

        return nearest_timestamp

    # Function to search and print StateOfCharge at the specified time
    def search_and_print_state_of_charge(filename, hour, minute):
        try:
            with open(filename, 'r') as file:
                lines = file.readlines()
            timestamp_pattern = r"\d{2}/\d{2}/\d{4} " + re.escape(hour + ":" + minute) + r":\d{2}"
            combined_pattern = rf"{timestamp_pattern}, Gauge Info,StateOfCharge=(\d+)%"

            matches = list(re.finditer(combined_pattern, "\n".join(lines)))

            if not matches:
                nearest_timestamp = find_nearest_timestamp("\n".join(lines), f"{hour}:{minute}")

                if nearest_timestamp:
                    print_to_text_widget(f"No time found at {hour}:{minute}, the latest time with 100% charge is: {nearest_timestamp}")
                    
                    for index, line in enumerate(lines):
                        if nearest_timestamp in line:
                            if index + 1 < len(lines):
                                print_to_text_widget(lines[index + 1].strip())
                            if index + 2 < len(lines):
                                print_to_text_widget(lines[index + 2].strip())
                            break

                else:
                    messagebox.showinfo("Information", "No times with 100% charge is found.")
            else:
                for match in matches:
                    state_of_charge = match.group(1)
                    print_to_text_widget(f"At {hour}:{minute} the State of charge is {state_of_charge}%")
        except Exception as e:
            print(f"Error reading the file {filename}: {str(e)}")
# Check if the file exists based on the generated filename
    file_on_usb = search_file(usb_drive_root, filename)
    if file_on_usb:
        if file_exists(file_on_usb):
            print(f"File {filename} exists.")
            # Read and print the content of the file
            content = read_file_content(file_on_usb)
            # Search for StateOfCharge around the specified time in the specified file
            search_and_print_state_of_charge(file_on_usb, hour, minute)
        else:
            print(f"File {filename} does not exist.")
    else:
        print(f"File {filename} not found on the USB drive.")

# Create a function to perform the actions and display results
def perform_usb_drive_actions():
    # Clear the result_text_widget
    result_text_widget.delete(1.0, tk.END)

    selected_drive_info = usb_drive_combobox.get()  # Get the selected USB drive info
    print(selected_drive_info)
    if not selected_drive_info:
        return  # No drive selected

    # Extract the drive letter from the selected drive info
    drive_letter = selected_drive_info.split(" ")[0].strip("()")
    print(drive_letter)
    
    # Construct the USB drive root path
    usb_drive_root = f"{drive_letter}\\"
    print(usb_drive_root)
    
    # Function to print messages to the result_text_widget
    def print_to_text_widget(message):
        result_text_widget.insert(tk.END, message + "\n")
        result_text_widget.see(tk.END)  # Scroll to the end

    # Function to print the entire content of 'USBSEL.lct'
    def print_entire_file(file_path):
        try:
            with open(file_path, 'r') as file:
                file_contents = file.read()
                print(file_contents)
                print(f"File Name: {file_path}:")
                print_to_text_widget(f"Serial Number: {file_contents}")
        except Exception as e:
            print_to_text_widget(f"Error reading the file {file_path}: {str(e)}")
 
    # Function to search for text matching the patterns in 'version.json' and print the matching lines
    def search_and_print_lines_version_json(file_path, patterns):
        try:
            with open(file_path, 'r') as file:
                file_contents = file.read()
                print(f"File Name: {file_path}:")
                for pattern in patterns:
                    matches = re.finditer(pattern, file_contents)
                    for match in matches:
                        print(match.group(0))
                        print_to_text_widget(match.group(0).replace('"', ''))
        except Exception as e:
            print_to_text_widget(f"Error reading the file {file_path}: {str(e)}")

    # Debugging message to indicate that the function is called
    print("Performing USB drive actions...")
    
    # Iterate over the list of file names to find
    for file_name in file_names_to_find:
        file_path_on_usb = search_file(usb_drive_root, file_name)
        if file_path_on_usb:
            if file_name == 'USBSEL.lct':
                print_entire_file(file_path_on_usb)
            elif file_name == 'version.json':
                search_and_print_lines_version_json(file_path_on_usb, text_patterns[file_name])
            
        else:
            print_to_text_widget(f"File {file_name} not found on the USB drive.")

# Define the pattern to match the desired line to find burnin time
pattern = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}, Power off,\((\d+) sec\. used\)"

# Function to find and extract the desired line from the file
def find_and_extract_line(filename, pattern):
    with open(filename, 'r') as file:
        for line in file:
            match = re.search(pattern, line)
            if match:
                return match.group(1) # Extract and return the matched part
    return None
# Function to recursively search for .log files in a directory
def search_log_files(root_dir):
    log_files = []
    for root, dirs, files in os.walk(root_dir):
        for file_name in files:
            if file_name.endswith(".log"):
                log_files.append(os.path.join(root, file_name))
    return log_files

# Function to search for burn-in times in a single file
def search_burnin_times_in_file(file_path, pattern):
    dates_times = []
    try:
        with open(file_path, 'r') as file:
            file_contents = file.read()
            matches = re.finditer(pattern, file_contents)
            for match in matches:
                date_time = match.group(0)
                burnin_time = int(match.group(1))
                dates_times.append((date_time, burnin_time))
    except Exception as e:
        pass
    return file_path, dates_times

def ask_date_selection(dates):
    """
    Displays a dialog with a Combobox for the user to select a date.
    Returns:
        The selected date as a string or None if the user closes the dialog without selecting.
    """
    def on_ok():
        nonlocal selected_date
        selected_date = combo.get()
        dialog.destroy()

    selected_date = None
    dialog = Toplevel()  # Create a new dialog window
    dialog.title("Date Selection")
    ttk.Label(dialog, text="There are multiple Burin Times. Please Select a date:").pack(padx=20, pady=10)
    
    # Create and populate the Combobox
    combo = ttk.Combobox(dialog, values=dates)
    if dates:
        combo.current(0)  # set first date as default
    combo.pack(padx=20, pady=10)

    ok_button = ttk.Button(dialog, text="OK", command=on_ok)
    ok_button.pack(pady=20)

    dialog.wait_window()  # Wait until the dialog is closed

    return selected_date

def view_burnin():
    # Search for .log files in the USB drive
    selected_drive_info = usb_drive_combobox.get()  # Get the selected USB drive info
    print(selected_drive_info)
    if not selected_drive_info:
        print_to_text_widget("No drive selected")
        return  # No drive selected

    # Extract the drive letter from the selected drive info
    drive_letter = selected_drive_info.split(" ")[0].strip("()")
    print(drive_letter)
    
    # Construct the USB drive root path
    usb_drive_root = f"{drive_letter}\\"
    log_files = search_log_files(usb_drive_root)

    if not log_files:
        print_to_text_widget("No .log files found on the USB drive.")
    else:
        # Use concurrent processing to search for burn-in times in .log files
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(lambda f: search_burnin_times_in_file(f, pattern), log_files):
                if result is not None:
                    results.append(result)
                    
    # Function to print messages to the result_text_widget
    def print_to_text_widget(message):
        result_text_widget.insert(tk.END, message + "\n")
        result_text_widget.see(tk.END)  # Scroll to the end

    # Filter out results with valid burn-in times
    valid_results = [(file_path, burnin_time) for file_path, burnin_time in results if burnin_time is not None]
    
     # Collecting all dates and times across files
    all_dates_times = [dt for _, date_times in valid_results for dt in date_times]

    # Extract valid burn-in times
    valid_time_values = [time[1] for time in all_dates_times if time[1] >= 25000]

    print(valid_time_values)
            
    # Extract valid dates
    valid_dates = list(set(date.split()[0] for date, time in all_dates_times if time >= 25000))

    if not valid_dates:
        print_to_text_widget("No valid burn-in times found.")
        return
    
    # If there's more than one valid date, ask the user to select
    if len(valid_dates) > 1:
        user_choice = ask_date_selection(valid_dates)
        if not user_choice:
            return

        # Filter results based on the selected date
        selected_results = [(date, time) for date, time in all_dates_times if date.startswith(user_choice)]
        largest_burnin_time = max(selected_results, key=lambda x: x[1])[1]
    else:
        # If there's only one valid date, use it directly
        largest_burnin_time = max([time for date, time in all_dates_times if date.startswith(valid_dates[0])])

    # Display the result for the largest burn-in time (from all or the selected date)
    print_to_text_widget(f"Burn-in Time: {largest_burnin_time} sec")

    if largest_burnin_time > 50400:
        print_to_text_widget("Burn-in time test is passed")
    elif 10000 <= largest_burnin_time <= 50400:
        print_to_text_widget("Burn-in time test is FAILED")
    else:
        print_to_text_widget(f"{log_files} contains invalid {largest_burnin_time} burn-in time.")

# Function to clear the everything
def clear_all():
    selected_drive_info = usb_drive_combobox.get()  # Get the selected USB drive info
    print(selected_drive_info)
    if not selected_drive_info:
        return  # No drive selected

    # Extract the drive letter from the selected drive info
    drive_letter = selected_drive_info.split(" ")[0].strip("()")
    print(drive_letter)
    
    # Construct the USB drive root path
    usb_drive_root = f"{drive_letter}\\"
    
    # Prompt user for confirmation
    root = tk.Tk()  # Creating a root window (hidden)
    root.withdraw()  # Hide the root window
    
    # Display message box
    response = messagebox.askyesno("Confirmation", f"Do you really want to clear everything from drive {drive_letter}?")
    
    if response:  # If user clicks 'Yes'
        shutil.rmtree(usb_drive_root)
    root.destroy()  # Destroy the hidden root window
    
# Function to handle the USB drive selection
def on_usb_drive_select(event):
    selected_drive_info = usb_drive_combobox.get()  # Get the selected USB drive info
    print(f"Selected USB Drive Info: {selected_drive_info}")

# Function to handle the refresh button click
def on_refresh_click():
    usb_drive_combobox['values'] = populate_usb_drives()

# Create a Combobox to select USB drives with names
usb_drive_combobox = ttk.Combobox(root, values=populate_usb_drives(), width=40)
usb_drive_combobox.grid(row=0, column=0, padx=10, pady=10, sticky='nw')

# Bind the selection event to the function
usb_drive_combobox.bind("<<ComboboxSelected>>", on_usb_drive_select)

refresh_button = ttk.Button(root, text="Refresh", command=on_refresh_click)
refresh_button.grid(padx=10, pady=50, row=0, column=0, sticky='nw')

# Create a button to trigger the file search and print function
select_button = ttk.Button(root, text="Select", command=perform_usb_drive_actions)
select_button.grid(row=0, column=1, padx=10, pady=10, sticky='nw')

# Create a button to clear the all data
select_button = ttk.Button(root, text="Clear X2", command=clear_all)
select_button.grid(row=3, column=0, padx=10, pady=10, sticky='nw')

# Create a button to trigger the burnin time calculation
burnin_button = ttk.Button(root, text="View Burnin", command=view_burnin)
burnin_button.grid(row=0, column=1, padx=10, pady=40, sticky='nw')

# Create a Text widget to display results
result_text_widget = tk.Text(root, wrap=tk.WORD, width=52, height=15) 
result_text_widget.grid(row=0, column=2, padx=10, pady=10, sticky='ne')

# Create a Scrollbar widget for the Text widget
scrollbar = ttk.Scrollbar(root, command=result_text_widget.yview)
scrollbar.grid(row=0, column=3, padx=10, pady=10, sticky='ns')

# Configure the Text widget to use the Scrollbar
result_text_widget.config(yscrollcommand=scrollbar.set)

# Create a button to update the calendar
update_button = ttk.Button(root, text="State of Charge", command=update_calendar)
update_button.grid(row=0, column=1, padx=10, pady=65)

# Create a DateEntry widget (you'll need to install tkcalendar library)
from tkcalendar import DateEntry

calendar_widget = DateEntry(root, width=12, background="darkblue", foreground="white", borderwidth=2)
calendar_widget.grid(row=0, column=0, columnspan=3, padx=10, pady=200, sticky='nw')

# Set the initial date to the current date
today = calendar.datetime.datetime.now()
calendar_widget.set_date(today)

# Create a label and an entry for hour input
hour_label = ttk.Label(root, text="Hour:")
hour_label.grid(row=1, column=0, padx=10, pady=10, sticky='nw')  

hour_entry = ttk.Entry(root)
hour_entry.grid(row=1, column=1, padx=10, pady=10, sticky='nw')

# Create a label and an entry for minute input
minute_label = ttk.Label(root, text="Minute:")
minute_label.grid(row=2, column=0, padx=10, pady=10, sticky='nw')  

minute_entry = ttk.Entry(root)
minute_entry.grid(row=2, column=1, padx=10, pady=10, sticky='nw') 

root.mainloop()
