import tkinter as tk
from tkinter import ttk, filedialog
import serial
import threading
import time
import json
import csv
from datetime import datetime

class BluetoothScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth Device Scanner")
        self.root.geometry("800x600")
        
        # Serial connection
        self.serial_port = None
        self.scanning = False
        
        # Device storage
        self.devices = {}
        self.device_history = []  # Store all readings for CSV export
        
        self.setup_gui()
        
    def setup_gui(self):
        # Control Frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # Port selection
        ttk.Label(control_frame, text="COM Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="COM3")
        self.port_entry = ttk.Entry(control_frame, textvariable=self.port_var, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Scan button
        self.scan_button = ttk.Button(control_frame, text="Start Scan", command=self.toggle_scan)
        self.scan_button.pack(side=tk.LEFT, padx=5)
        
        # Export button
        self.export_button = ttk.Button(control_frame, text="Export CSV", command=self.export_csv)
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Device list
        columns = ("name", "address", "rssi", "proximity", "last_seen")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        
        # Define headings
        self.tree.heading("name", text="Device Name")
        self.tree.heading("address", text="MAC Address")
        self.tree.heading("rssi", text="RSSI")
        self.tree.heading("proximity", text="Proximity")
        self.tree.heading("last_seen", text="Last Seen")
        
        # Define column widths
        self.tree.column("name", width=200)
        self.tree.column("address", width=150)
        self.tree.column("rssi", width=100)
        self.tree.column("proximity", width=100)
        self.tree.column("last_seen", width=150)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def calculate_proximity(self, rssi):
        """Calculate proximity based on RSSI value"""
        if rssi >= -50:
            return "Very Close"
        elif -50 > rssi >= -70:
            return "Close"
        else:
            return "Far"
    
    def update_device_list(self, device_data):
        """Update the device list with new data"""
        address = device_data.get("address")
        if not address:
            return
            
        rssi = int(device_data.get("rssi", 0))
        proximity = self.calculate_proximity(rssi)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store reading in history
        history_entry = {
            "name": device_data.get("name", "Unknown"),
            "address": address,
            "rssi": rssi,
            "proximity": proximity,
            "timestamp": timestamp
        }
        self.device_history.append(history_entry)
        
        # Update existing device or add new one
        if address in self.devices:
            self.tree.item(self.devices[address], values=(
                device_data.get("name", "Unknown"),
                address,
                rssi,
                proximity,
                timestamp
            ))
        else:
            item_id = self.tree.insert("", tk.END, values=(
                device_data.get("name", "Unknown"),
                address,
                rssi,
                proximity,
                timestamp
            ))
            self.devices[address] = item_id
    
    def export_csv(self):
        """Export device history to CSV file"""
        if not self.device_history:
            tk.messagebox.showwarning("No Data", "No device data available to export.")
            return
            
        try:
            # Get save file location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"bluetooth_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if filename:
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = ['timestamp', 'name', 'address', 'rssi', 'proximity']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for entry in self.device_history:
                        writer.writerow(entry)
                        
                tk.messagebox.showinfo("Success", f"Data exported successfully to {filename}")
        
        except Exception as e:
            tk.messagebox.showerror("Export Error", f"Error exporting data: {str(e)}")
    
    def read_jdy19(self):
        """Read data from JDY-19 sensor"""
        while self.scanning:
            try:
                if self.serial_port and self.serial_port.is_open:
                    data = self.serial_port.readline().decode().strip()
                    if data:
                        try:
                            device_data = json.loads(data)
                            self.root.after(0, self.update_device_list, device_data)
                        except json.JSONDecodeError:
                            print(f"Invalid data received: {data}")
                time.sleep(0.1)
            except Exception as e:
                print(f"Error reading data: {e}")
                self.stop_scan()
                break
    
    def start_scan(self):
        """Start scanning for devices"""
        try:
            port = self.port_var.get()
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            self.scanning = True
            self.scan_button.configure(text="Stop Scan")
            
            # Start reading thread
            self.read_thread = threading.Thread(target=self.read_jdy19)
            self.read_thread.daemon = True
            self.read_thread.start()
            
        except Exception as e:
            print(f"Error starting scan: {e}")
            self.stop_scan()
    
    def stop_scan(self):
        """Stop scanning for devices"""
        self.scanning = False
        if self.serial_port:
            self.serial_port.close()
        self.scan_button.configure(text="Start Scan")
    
    def toggle_scan(self):
        """Toggle scanning on/off"""
        if self.scanning:
            self.stop_scan()
        else:
            self.start_scan()

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothScanner(root)
    root.mainloop()