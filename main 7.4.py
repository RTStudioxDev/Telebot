import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font, simpledialog
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest
from telethon.errors import FloodWaitError
from telethon.tl.types import InputPeerChannel, InputPeerChat
import asyncio
import json
import os
import sys
import time
import logging
from dotenv import load_dotenv
from datetime import datetime
from cryptography.fernet import Fernet
import threading
import webbrowser
import atexit
import uuid
import hashlib
import platform
from licensing.models import LicenseKey
from licensing.methods import Key, Helpers
import requests

# Global variable to control the transfer process
transfer_active = False
pause_event = threading.Event()

# Decrypt and load the config file
def load_encrypted_config():
    try:
        # Load the encryption key
        with open("config_key.key", "rb") as key_file:
            key = key_file.read()

        # Decrypt the config file
        fernet = Fernet(key)
        with open("config.encrypted", "rb") as encrypted_file:
            encrypted_config = encrypted_file.read()
        decrypted_config = fernet.decrypt(encrypted_config).decode()

        # Load the decrypted config file
        config = json.loads(decrypted_config)
        return config
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถถอดรหัสหรือลบไฟล์ config: {e}")
        sys.exit(1)

# Save and encrypt the config file
def save_encrypted_config(config):
    try:
        # Load the encryption key
        with open("config_key.key", "rb") as key_file:
            key = key_file.read()

        # Encrypt the config file
        fernet = Fernet(key)
        encrypted_config = fernet.encrypt(json.dumps(config).encode())

        # Save the encrypted config file
        with open("config.encrypted", "wb") as encrypted_file:
            encrypted_file.write(encrypted_config)

        print("ไฟล์ Config บันทึกสำเร็จแล้ว.")
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเข้ารหัสหรือบันทึกไฟล์ config: {e}")
        sys.exit(1)

# Define the preferred font and size
PREFERRED_FONT = "Prompt"
FONT_SIZE = 9

def validate_license_key(key: str) -> bool:
    """Validate the license key using cryptolen with better error handling"""
    try:
        RSAPubKey = "<RSAKeyValue><Modulus>1qxEd+cAB4iYRcxB91f9l3+7CTAO1UAmbg6Y6W4IkJWfGq1uC/0L0C6iWe+tFZibRQtLABAFiqDkPo+NVmFycffEQgBGCm2MS4wnBpPedQCfUO7YytoPY8SdURi7+BgbhjXP55ntsy6r6VD2UhV+kkrRMi7J7E/DTh81aXkJIxKMLpLJiXJhdwnFav9FYnols3teCiapWhlYSUMtj5yiIqj0nfPSER3ywYJspEs9FWnEKw6Q+ip9soksLz5YuSFsUr1N/Q1M1YzN8DcX2Yz02xHK/12UaXs7xn5rm7+qZ+ajpbv5Py3XSJ+VRcQ42FvjljggsYMOnX9ANcCiDyAS8w==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"
        auth = "WyIxMDU4MzgyMDgiLCJ4WkhweFh4Zlo0dFpHZmpvZUNiaWNLUlVHRFBvb0pHcmNvdDBob0dyIl0="
        
        # First try the online validation
        try:
            result = Key.activate(
                token=auth,
                rsa_pub_key=RSAPubKey,
                product_id=29478,
                key=key,
                machine_code=Helpers.GetMachineCode()
            )
            
            if result[0] is None or not Helpers.IsOnRightMachine(result[0]):
                return False
            
            return True
        except requests.exceptions.RequestException:
            # If online validation fails, fall back to offline validation
            license_key = LicenseKey.from_string(key)
            if not license_key.validate_signature(RSAPubKey):
                return False
                
            # Check if license is expired
            if license_key.is_expired():
                return False
                
            # Additional offline checks can be added here
            return True
            
    except Exception as e:
        print(f"License validation error: {e}")
        return False

def check_key(config):
    """Check if the key is valid and stored in config"""
    # First check if we have a stored key
    stored_key = config.get("LICENSE_KEY")
    
    if stored_key:
        # Validate the stored key
        if validate_license_key(stored_key):
            return True  # Valid key found
    
    # If no valid stored key, prompt user for a new one
    while True:
        new_key = show_custom_input("License Key", "กรุณากรอก License Key:")
        if not new_key:
            show_custom_error("ข้อผิดพลาด", "ต้องกรอก License Key เพื่อใช้งานโปรแกรม")
            sys.exit(1)
            
        if validate_license_key(new_key):
            # Save the valid key to config
            config["LICENSE_KEY"] = new_key
            save_encrypted_config(config)
            show_custom_info("สำเร็จ", "License Key ถูกบันทึกเรียบร้อยแล้ว")
            return True
        else:
            show_custom_error("ข้อผิดพลาด", "License Key ไม่ถูกต้อง กรุณาลองอีกครั้ง")

def show_custom_error(title, message):
    """Show a custom error dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Create a custom error dialog
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("300x120")
    dialog.configure(bg="#f0f0f0")
    
    # Add a label for the message
    label = ttk.Label(dialog, text=message, font=(PREFERRED_FONT, FONT_SIZE), background="#f0f0f0")
    label.pack(pady=20)

    # Add an "OK" button
    button = ttk.Button(dialog, text="OK", command=dialog.destroy)
    button.pack(pady=10)

    # Center the dialog on the screen
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"+{x}+{y}")

    # Wait for the dialog to close
    dialog.wait_window()

def show_custom_info(title, message):
    """Show a custom info dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Create a custom info dialog
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("300x120")
    dialog.configure(bg="#f0f0f0")

    # Add a label for the message
    label = ttk.Label(dialog, text=message, font=(PREFERRED_FONT, FONT_SIZE), background="#f0f0f0")
    label.pack(pady=20)

    # Add an "OK" button
    button = ttk.Button(dialog, text="OK", command=dialog.destroy)
    button.pack(pady=10)

    # Center the dialog on the screen
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"+{x}+{y}")

    # Wait for the dialog to close
    dialog.wait_window()

def show_custom_input(title, prompt):
    """Show a custom input dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Create a custom input dialog
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("300x120")
    dialog.configure(bg="#f0f0f0")

    # Add a label for the prompt
    label = ttk.Label(dialog, text=prompt, font=(PREFERRED_FONT, FONT_SIZE), background="#f0f0f0")
    label.pack(pady=5)

    # Add an entry widget for user input
    entry = ttk.Entry(dialog, font=(PREFERRED_FONT, FONT_SIZE))
    entry.pack(pady=10)

    # Add "OK" and "Cancel" buttons
    user_input = None

    def on_ok():
        nonlocal user_input
        user_input = entry.get()
        dialog.destroy()

    def on_cancel():
        nonlocal user_input
        user_input = None
        dialog.destroy()

    button_frame = ttk.Frame(dialog)
    button_frame.pack(pady=10)

    ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
    ok_button.pack(side="left", padx=5)

    cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
    cancel_button.pack(side="right", padx=5)

    # Center the dialog on the screen
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"+{x}+{y}")

    # Wait for the dialog to close
    dialog.wait_window()

    return user_input

# Load settings from config.json
def load_config():
    """Load settings from config.json"""
    try:
        return load_encrypted_config()
    except FileNotFoundError:
        # Create config.json if it doesn't exist
        default_config = {
            "ACCOUNTS": {},
            "SOURCE_GROUP": "",
            "DESTINATION_GROUP": "",
            "DELAY_BETWEEN_USERS": 2,
            "MAX_MEMBERS_TO_PULL": 0,
            "LICENSE_KEY": "",
            "HELP_LINK": "",
            "CONTACT": ""
        }
        save_encrypted_config(default_config)
        return default_config

# Save settings to config.json
def save_config(config):
    """Save settings to config.json"""
    try:
        save_encrypted_config(config)
        messagebox.showinfo("สำเร็จ", "บันทึกเรียบร้อย")
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกการตั้งค่า: {e}")

# GUI Application
class TelegramMemberTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Bot V7.4 @RTStudio-Dev✅")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")

        # Load the icon as soon as the application starts
        self.load_icon()

        # Load settings
        self.config = load_config()

        # Check License Key
        check_key(self.config)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.thai_font = font.Font(family="Prompt", size=9)
        self.style.configure(".", font=self.thai_font)

        self.config = load_config()

        # Variables
        self.api_id = tk.StringVar(value="")
        self.api_hash = tk.StringVar(value="")
        self.phone_number = tk.StringVar(value="")
        self.source_group = tk.StringVar(value=self.config.get("SOURCE_GROUP", ""))
        self.destination_group = tk.StringVar(value=self.config.get("DESTINATION_GROUP", ""))
        self.delay_between_users = tk.IntVar(value=self.config.get("DELAY_BETWEEN_USERS", 2))
        self.max_members_to_pull = tk.IntVar(value=self.config.get("MAX_MEMBERS_TO_PULL", 0))
        self.help_link = tk.StringVar(value=self.config.get("HELP_LINK", ""))
        self.contact = tk.StringVar(value=self.config.get("CONTACT", ""))
        self.terms_accepted = tk.BooleanVar(value=False)

        # Transfer control variables
        self.transfer_active = False
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()

        self.confirm_terms()
        self.create_widgets()
        self.show_expiration_date()  # Add this line to show expiration date

    def show_expiration_date(self):
        """Display the license key expiration date"""
        try:
            RSAPubKey = "<RSAKeyValue><Modulus>1qxEd+cAB4iYRcxB91f9l3+7CTAO1UAmbg6Y6W4IkJWfGq1uC/0L0C6iWe+tFZibRQtLABAFiqDkPo+NVmFycffEQgBGCm2MS4wnBpPedQCfUO7YytoPY8SdURi7+BgbhjXP55ntsy6r6VD2UhV+kkrRMi7J7E/DTh81aXkJIxKMLpLJiXJhdwnFav9FYnols3teCiapWhlYSUMtj5yiIqj0nfPSER3ywYJspEs9FWnEKw6Q+ip9soksLz5YuSFsUr1N/Q1M1YzN8DcX2Yz02xHK/12UaXs7xn5rm7+qZ+ajpbv5Py3XSJ+VRcQ42FvjljggsYMOnX9ANcCiDyAS8w==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"
            auth = "WyIxMDU4MzgyMDgiLCJ4WkhweFh4Zlo0dFpHZmpvZUNiaWNLUlVHRFBvb0pHcmNvdDBob0dyIl0="
            
            key = self.config.get("LICENSE_KEY", "")
            if not key:
                return
                
            result = Key.activate(
                token=auth,
                rsa_pub_key=RSAPubKey,
                product_id=29478,
                key=key,
                machine_code=Helpers.GetMachineCode()
            )
            
            if result[0] is not None:
                license_key = result[0]
                if hasattr(license_key, 'expires'):
                    exp_date = license_key.expires.strftime("%d-%m-%Y")
                    self.log_text.insert(tk.END, f"วันหมดอายุของคุณคือ: {exp_date} (วัน-เดือน-ปี)\n")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการตรวจสอบวันหมดอายุ: {e}")

    def load_icon(self):
        """Load the application icon with multiple fallback options"""
        icon_paths = [
            "Ico.ico",  # Windows icon
            os.path.join(os.path.dirname(__file__), "Ico.ico"),  # Check in script directory
            os.path.join(sys._MEIPASS, "Ico.ico") if hasattr(sys, '_MEIPASS') else None  # For PyInstaller
        ]
    
        # Remove None values from paths
        icon_paths = [path for path in icon_paths if path is not None]
    
        loaded = False
        for icon_path in icon_paths:
            try:
                if icon_path.endswith('.ico'):
                    self.root.iconbitmap(icon_path)
                    loaded = True
                    break
            except Exception as e:
                print(f"ไม่สามารถโหลดไอคอนจาก {icon_path}: {e} ได้...")
                continue
    
        if not loaded:
            print("คำเตือน: ไม่สามารถโหลดไอคอนได้")

    def confirm_terms(self):
        try:
            with open("terms.txt", "r", encoding="utf-8") as terms_file:
                terms_content = terms_file.read()
        except FileNotFoundError:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบไฟล์ terms.txt")
            sys.exit(1)

        if messagebox.askyesno("ข้อกำหนดในการให้บริการ", f"{terms_content}\n\nคุณยอมรับข้อกำหนดในการให้บริการหรือไม่?"):
            self.terms_accepted.set(True)
        else:
            messagebox.showinfo("ข้อมูล", "คุณต้องยอมรับข้อกำหนดในการให้บริการเพื่อใช้โปรแกรมนี้")
            sys.exit(0)

    def create_widgets(self):
        """Create and arrange GUI elements"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="การตั้งค่า", padding="10")
        config_frame.pack(fill="x", pady=5)

        labels = [
            ("กลุ่มเป้าหมาย:", self.source_group),
            # ("จำนวนสมาชิกที่จะดึง (0 คือไม่จำกัด):", self.max_members_to_pull),
        ]

        for i, (label_text, variable) in enumerate(labels):
            # Increase the length and height of the Label
            label = ttk.Label(
                config_frame,
                text=label_text,
                font=("Prompt", 9),  # Increase font size
                width=10,             # Adjust label width
                anchor="w",           # Align text to the left
                padding=(2, 5)       # Add padding to make the label taller
            )
            label.grid(row=i, column=0, sticky="w", pady=5)
        
            if isinstance(variable, tk.IntVar):
                entry = ttk.Entry(
                    config_frame,
                    textvariable=variable,
                    font=("Prompt", 9),  # Increase font size
                    width=50              # Adjust entry width
                )
                entry.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
            else:
                entry = ttk.Entry(
                    config_frame,
                    textvariable=variable,
                    font=("Prompt", 9),  # Increase font size
                    width=50              # Adjust entry width
                )
                entry.grid(row=i, column=1, sticky="ew", padx=5, pady=5)

        group_button_frame = ttk.Frame(config_frame)
        group_button_frame.grid(row=i, column=0, columnspan=2, pady=2, sticky="e")

        ttk.Button(
            group_button_frame,
            text="บันทึก",
            command=self.save_group_settings
        ).pack(side="right", padx=15)

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="บันทึกการทำงาน", padding="10")
        log_frame.pack(fill="both", expand=True, pady=5)

        # Increase the length of the text box (ScrolledText)
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=80,  # Adjust text box width
            height=20,  # Adjust text box height
            font=("Prompt", 9)  # Increase font size
        )
        self.log_text.pack(fill="both", expand=True)

        # Redirect logs to GUI
        self.setup_logging()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        # Add control buttons (Start, Pause, Stop)
        control_button_frame = ttk.Frame(button_frame)
        control_button_frame.pack(side="left", padx=5)

        self.start_button = ttk.Button(control_button_frame, text="เริ่มการโอนย้าย", command=self.start_transfer)
        self.start_button.pack(side="left", padx=5)

        self.pause_button = ttk.Button(control_button_frame, text="หยุดชั่วคราว", command=self.pause_transfer, state=tk.DISABLED)
        self.pause_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(control_button_frame, text="หยุดการทำงาน", command=self.stop_transfer, state=tk.DISABLED)
        self.stop_button.pack(side="left", padx=5)

        # Add other buttons
        ttk.Button(button_frame, text="ตั้งค่า", command=self.open_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="ออก", command=self.root.quit).pack(side="right", padx=5)
        ttk.Button(button_frame, text="ช่วยเหลือ", command=self.open_help_link).pack(side="right", padx=5)
        ttk.Button(button_frame, text="ติดต่อ", command=self.open_contact).pack(side="right", padx=5)

        self.log_text.insert(tk.END, "@Copyright : RTStudio-XCODE💻\n")
        self.log_text.insert(tk.END, "Telegram : t.me/og999nine\n")
        self.log_text.insert(tk.END, "❌โปรดอ่านคำเตือนก่อนใช้งาน❌\n")
        self.log_text.insert(tk.END, "⚠️ข้อควรระวัง⚠️\n")
        self.log_text.insert(tk.END, "🟡1 บัญชีเพิ่มได้ประมาณ 50 คนหากมากกว่านั้นจะติดลิมิต 30 นาทีถึง 24 ชั่วโมง\n")
        self.log_text.insert(tk.END, "🟡หากติดลิมิตหรือเพิ่มไปแล้วประมาณ 50 คนให้เปลี่ยนบัญชีในการดึงใหม่หลีกเลี่ยงการโดนแบนจากเทเรแกรม\n")
        self.log_text.insert(tk.END, "❌หลีกเลี่ยงการใช้บัญชีที่ติดลิมิตมาดึงซ้ำไม่งั้นจะทำให้บัญชีแดงหรือโดนแบนได้\n")
        self.log_text.insert(tk.END, " \n")
        self.log_text.insert(tk.END, "🆘หากโปรแกรมมีปัญหาให้กดปุ่มติดต่อหาผู้พัฒนาได้เลยครับ🆘\n")

    def save_group_settings(self):
        """บันทึกการตั้งค่ากลุ่ม """
        try:
            # ตรวจสอบข้อมูลก่อนบันทึก
            source = self.source_group.get().strip()
            destination = self.destination_group.get().strip()
        
            if not source or not destination:
                messagebox.showerror("ข้อผิดพลาด", "กรุณากรอกข้อมูลกลุ่มเป้าหมายและกลุ่มของคุณให้ครบถ้วน")
                return

            # บันทึกข้อมูล
            self.config["SOURCE_GROUP"] = source
            self.config["DESTINATION_GROUP"] = destination
            save_encrypted_config(self.config)
        
            # แสดงผลลัพธ์
            self.log_text.insert(tk.END, "บันทึกการตั้งค่ากลุ่มสำเร็จ!\n")
            self.log_text.insert(tk.END, f"กลุ่มเป้าหมาย: {source}\n")
            self.log_text.insert(tk.END, f"กลุ่มของคุณ: {destination}\n")
            self.log_text.see(tk.END)
            messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่ากลุ่มเรียบร้อยแล้ว")
        
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดขณะบันทึก: {str(e)}")
            self.log_text.insert(tk.END, f"ERROR: {str(e)}\n")

    def open_help_link(self):
        help_link = self.help_link.get()
        if help_link:
            webbrowser.open(help_link)
        else:
            messagebox.showinfo("ข้อมูล", "ไม่มีลิงก์ช่วยเหลือที่ระบุในการตั้งค่า")

    def open_contact(self):
        contact = self.contact.get()
        if contact:
            webbrowser.open(contact)
        else:
            messagebox.showinfo("ข้อมูล", "ไม่มีลิงก์ติดต่อที่ระบุในการตั้งค่า")

    def open_settings(self):
        """Open settings window"""
        self.settings_window = tk.Toplevel(self.root)  # Store settings_window as an attribute
        self.settings_window.title("แก้ไขการตั้งค่า")
        self.settings_window.geometry("400x325")  # Adjust window size
        self.settings_window.configure(bg="#dedbd7")

        # Variables for settings
        self.settings_vars = {
            "เบอร์โทรศัพท์": tk.StringVar(value=self.config.get("PHONE_NUMBER", "")),
            "API_ID": tk.StringVar(value=self.config.get("API_ID", "")),
            "API_HASH": tk.StringVar(value=self.config.get("API_HASH", "")),
            "กลุ่มตัวเอง": tk.StringVar(value=self.config.get("DESTINATION_GROUP", "")),
            "ความไวในการดึง": tk.IntVar(value=self.config.get("DELAY_BETWEEN_USERS", 2)),
            "จำนวนสมาชิกที่จะดึง": tk.IntVar(value=self.config.get("MAX_MEMBERS_TO_PULL", 0)),
        }

        # Create settings editor
        for i, (key, var) in enumerate(self.settings_vars.items()):
            ttk.Label(self.settings_window, text=key, font=("Prompt", 9), width=10, anchor="w").grid(
                row=i, column=0, padx=10, pady=10, sticky="w"
            )
            if key == "เบอร์โทรศัพท์":
                phone_numbers = list(self.config.get("ACCOUNTS", {}).keys())
                self.phone_combobox = ttk.Combobox(
                    self.settings_window,
                    textvariable=var,
                    values=phone_numbers,
                    font=("Prompt", 9),  # Increase font size
                    width=30              # Adjust entry width
                )
                self.phone_combobox.grid(row=i, column=1, padx=10, pady=10, sticky="ew")
                self.phone_combobox.bind("<<ComboboxSelected>>", self.update_api_credentials)
            elif key in ["API_ID", "API_HASH"]:
                # Make API_ID and API_HASH fields read-only
                entry = ttk.Entry(
                    self.settings_window,
                    textvariable=var,
                    font=("Prompt", 9),  # Increase font size
                    width=30,             # Adjust entry width
                    state="readonly"      # Set to read-only
                )
                entry.grid(row=i, column=1, padx=10, pady=10, sticky="ew")
            else:
                entry = ttk.Entry(
                    self.settings_window,
                    textvariable=var,
                    font=("Prompt", 9),  # Increase font size
                    width=30              # Adjust entry width
                )
                entry.grid(row=i, column=1, padx=10, pady=10, sticky="ew")

        # Add new account and save buttons
        button_frame = ttk.Frame(self.settings_window)
        button_frame.grid(row=len(self.settings_vars), column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="เพิ่มบัญชีใหม่", command=self.add_new_account).pack(side="left", padx=10)
        ttk.Button(button_frame, text="บันทึก", command=lambda: self.save_settings(self.settings_vars)).pack(side="left", padx=10)

    def update_api_credentials(self, event=None):
        """Update API ID and API Hash when a phone number is selected"""
        selected_phone = self.settings_vars["เบอร์โทรศัพท์"].get()
        if selected_phone in self.config.get("ACCOUNTS", {}):
            api_id = self.config["ACCOUNTS"][selected_phone]["API_ID"]
            api_hash = self.config["ACCOUNTS"][selected_phone]["API_HASH"]
            self.settings_vars["API_ID"].set(api_id)
            self.settings_vars["API_HASH"].set(api_hash)

    def add_new_account(self):
        """Add a new account"""
        new_account_window = tk.Toplevel(self.root)
        new_account_window.title("เพิ่มบัญชีใหม่")
        new_account_window.geometry("400x250")
        new_account_window.configure(bg="#dedbd7")  # Set background to #dedbd7
        

        ttk.Label(new_account_window, text="เบอร์โทรศัพท์", font=self.thai_font).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        new_phone = ttk.Entry(new_account_window, font=self.thai_font)
        new_phone.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(new_account_window, text="API ID", font=self.thai_font).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        new_api_id = ttk.Entry(new_account_window, font=self.thai_font)
        new_api_id.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ttk.Label(new_account_window, text="API Hash", font=self.thai_font).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        new_api_hash = ttk.Entry(new_account_window, font=self.thai_font)
        new_api_hash.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        def save_new_account():
            phone = new_phone.get()
            api_id = new_api_id.get()
            api_hash = new_api_hash.get()
            if phone and api_id and api_hash:
                self.config["ACCOUNTS"][phone] = {"API_ID": api_id, "API_HASH": api_hash}
                save_config(self.config)
                messagebox.showinfo("สำเร็จ", "เพิ่มบัญชีเรียบร้อยแล้ว")
                new_account_window.destroy()
            else:
                messagebox.showerror("ข้อผิดพลาด", "กรุณากรอกข้อมูลให้ครบทุกช่อง")

        ttk.Button(new_account_window, text="บันทึก", command=save_new_account).grid(row=3, column=0, columnspan=2, pady=10)

    def save_settings(self, settings_vars):
        """Save settings to config.json"""
        try:
            # Update all values from settings_vars to config
            self.config["API_ID"] = settings_vars["API_ID"].get()
            self.config["API_HASH"] = settings_vars["API_HASH"].get()
            self.config["PHONE_NUMBER"] = settings_vars["เบอร์โทรศัพท์"].get()
            self.config["DESTINATION_GROUP"] = settings_vars["กลุ่มตัวเอง"].get()
            self.config["DELAY_BETWEEN_USERS"] = settings_vars["ความไวในการดึง"].get()
            self.config["MAX_MEMBERS_TO_PULL"] = settings_vars["จำนวนสมาชิกที่จะดึง"].get()

            # Save new account or update existing account
            selected_phone = settings_vars["เบอร์โทรศัพท์"].get()
            if selected_phone:
                if "ACCOUNTS" not in self.config:
                    self.config["ACCOUNTS"] = {}
                self.config["ACCOUNTS"][selected_phone] = {
                    "API_ID": settings_vars["API_ID"].get(),
                    "API_HASH": settings_vars["API_HASH"].get(),
                }

            # Save settings to config.json
            save_config(self.config)

            # Update current values in GUI
            self.api_id.set(settings_vars["API_ID"].get())
            self.api_hash.set(settings_vars["API_HASH"].get())
            self.phone_number.set(settings_vars["เบอร์โทรศัพท์"].get())
            self.destination_group.set(settings_vars["กลุ่มตัวเอง"].get())
            self.delay_between_users.set(settings_vars["ความไวในการดึง"].get())
            self.max_members_to_pull.set(settings_vars["จำนวนสมาชิกที่จะดึง"].get())

            # Close settings window after successful save
            self.settings_window.destroy()

            messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว")
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกการตั้งค่า: {e}")

    def setup_logging(self):
        class GuiLogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + "\n")
                self.text_widget.see(tk.END)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        gui_handler = GuiLogHandler(self.log_text)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)

    def start_transfer(self):
        if not self.terms_accepted.get():
            messagebox.showerror("ข้อผิดพลาด", "คุณต้องยอมรับข้อกำหนดในการให้บริการเพื่อดำเนินการต่อ")
            return

        if not all([self.api_id.get(), self.api_hash.get(), self.phone_number.get(),
                    self.source_group.get(), self.destination_group.get()]):
            messagebox.showerror("ข้อผิดพลาด", "กรุณากรอกข้อมูลให้ครบทุกช่อง")
            return

        # Reset stop event and clear pause event
        self.stop_event.clear()
        self.pause_event.clear()
        
        # Update button states
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        
        # Start the transfer in a new thread
        self.transfer_thread = threading.Thread(target=self.run_transfer, daemon=True)
        self.transfer_thread.start()

    def pause_transfer(self):
        if self.pause_event.is_set():
            # Resume the transfer
            self.pause_event.clear()
            self.pause_button.config(text="หยุดชั่วคราว")
            logging.info("ดำเนินการดึงสมาชิกต่อ...")
        else:
            # Pause the transfer
            self.pause_event.set()
            self.pause_button.config(text="ดำเนินการต่อ")
            logging.info("การดึงสมาชิกถูกหยุดชั่วคราว...")

    def stop_transfer(self):
        # Set the stop event to terminate the transfer
        self.stop_event.set()
        
        # Also clear any pause that might be in effect
        self.pause_event.clear()
        
        # Update button states
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        
        logging.info("การดึงสมาชิกถูกหยุดแล้ว")

    def run_transfer(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            client = TelegramClient('session_bot', self.api_id.get(), self.api_hash.get(), loop=loop)

            with client:
                if not loop.run_until_complete(self.authorize_client(client)):
                    return

                source_group = loop.run_until_complete(self.get_entity(client, self.source_group.get()))
                destination_group = loop.run_until_complete(self.get_entity(client, self.destination_group.get()))

                members = loop.run_until_complete(self.get_participants(client, source_group, self.max_members_to_pull.get()))

                loop.run_until_complete(self.add_members(client, destination_group, members, self.delay_between_users.get()))

            logging.info("การดึงสมาชิกเสร็จสมบูรณ์")
            
            # Reset button states when transfer completes
            self.root.after(0, lambda: [
                self.start_button.config(state=tk.NORMAL),
                self.pause_button.config(state=tk.DISABLED),
                self.stop_button.config(state=tk.DISABLED)
            ])
            
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาด: {e}")
            
            # Reset button states on error
            self.root.after(0, lambda: [
                self.start_button.config(state=tk.NORMAL),
                self.pause_button.config(state=tk.DISABLED),
                self.stop_button.config(state=tk.DISABLED)
            ])

    async def authorize_client(self, client):
        if not await client.is_user_authorized():
            await client.send_code_request(self.phone_number.get())
            code = input("กรุณากรอกรหัส 6 หลักที่คุณได้รับ: ")
            await client.sign_in(self.phone_number.get(), code)
        return True

    async def get_entity(self, client, username):
        return await client.get_entity(username)

    async def get_participants(self, client, group, limit):
        return await client.get_participants(group, limit=limit if limit > 0 else None)

    async def add_members(self, client, destination_group, members, delay):
        for user in members:
            # Check if we should stop
            if self.stop_event.is_set():
                logging.info("หยุดการดึงสมาชิกแล้ว")
                return
                
            # Check if we should pause
            while self.pause_event.is_set():
                if self.stop_event.is_set():
                    return
                await asyncio.sleep(1)  # Sleep for 1 second while paused
                
            try:
                if hasattr(destination_group, "broadcast") or hasattr(destination_group, "megagroup"):
                    await client(InviteToChannelRequest(
                        channel=InputPeerChannel(destination_group.id, destination_group.access_hash),
                        users=[user]
                    ))
                else:
                    await client(AddChatUserRequest(
                        chat_id=destination_group.id,
                        user_id=user.id,
                        fwd_limit=0
                    ))
                logging.info(f"เพิ่ม {user.first_name} {user.last_name} ไปยังกลุ่มของคุณแล้ว")
            except FloodWaitError as e:
                # Convert seconds to hours, minutes, seconds
                hours = e.seconds // 3600
                minutes = (e.seconds % 3600) // 60
                seconds = e.seconds % 60
                if hours > 0:
                    wait_time = f"{hours} ชั่วโมง {minutes} นาที {seconds} วินาที"
                elif minutes > 0:
                    wait_time = f"{minutes} นาที {seconds} วินาที"
                else:
                    wait_time = f"{seconds} วินาที"
                
                logging.warning(f"บัญชีนี้เกินขีดจำกัดอัตรา ต้องรอ {wait_time}... ถึงจะสามารถทงานต่อได้")
                logging.warning(f"โปรดเปลี่ยนบัญชีในการดึงเพื่อหลีกเลี่ยงบัญชีแดงหรือโดนแบน: หากติดลิมิตบ่อยเกินไป")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logging.error(f"ไม่สามารถเพิ่ม {user.first_name} {user.last_name}: {e} ได้")
            
            # Add delay between each user
            await asyncio.sleep(delay)

if __name__ == "__main__":
    # Create a hidden root window for key verification
    temp_root = tk.Tk()
    temp_root.withdraw()  # Hide the temporary root window

    # Load settings and check key
    config = load_config()
    check_key(config)

    # Destroy the temporary root window
    temp_root.update()  # Process any pending events
    temp_root.destroy()

    # Create the main application window
    root = tk.Tk()
    app = TelegramMemberTransferApp(root)
    root.mainloop()