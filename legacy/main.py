import sys
import os
from coordinator import LegalResearchCoordinator

def main():
    print("Welcome to the Legal Research Coordinator (CLI).")
    print("Initializing system... (this may take a moment to load models)")
    
    try:
        coordinator = LegalResearchCoordinator()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    print("\n--- Commands ---")
    print("/upload <path_to_txt_file> : Load a document context")
    print("/quit                      : Exit")
    print("----------------")
    
    while True:
        try:
            user_input = input("\n>> ").strip()
            if not user_input:
                continue
                
            if user_input.lower() == "/quit":
                print("Exiting...")
                break
                
            if user_input.lower().startswith("/upload "):
                path = user_input[8:].strip()
                if not os.path.exists(path):
                    print(f"Error: File not found at {path}")
                    continue
                    
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    coordinator.process_uploaded_document(os.path.basename(path), text)
                    print(f"Successfully processed {path}")
                except Exception as e:
                    print(f"Error reading file: {e}")
                continue
                
            # Regular Query
            print("Researching...")
            response = coordinator.run_query(user_input)
            print("\n" + "="*40)
            print(response)
            print("="*40)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
