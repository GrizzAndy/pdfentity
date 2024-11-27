import fitz  # PyMuPDF
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import logging
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'pdf_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def process_pdf(pdf_path, criteria_file):
    try:
        # Load the JSON criteria
        with open(criteria_file, 'r') as file:
            criteria_data = json.load(file)

        doc = fitz.open(pdf_path)
        pdf_data = []

        for document in criteria_data["documents"]:
            document_name = document.get("document_name", "Unknown")

            for page_number in range(len(doc)):
                page = doc.load_page(page_number)
                
                # Check if all criteria sets are met for this page
                all_criteria_sets_met = True
                criteria_results = {}  # Store results for all criteria sets
                
                # First, check all criteria sets
                for criteria_set in document.get("criteria_sets", []):
                    try:
                        if not isinstance(criteria_set, dict):
                            logger.warning(f"Invalid criteria_set: {criteria_set}")
                            all_criteria_sets_met = False
                            break

                        criteria = criteria_set.get("criteria", "")
                        criteria_box = criteria_set.get("criteria_box", None)

                        if not criteria_box or not isinstance(criteria_box, dict):
                            logger.warning(f"Invalid or missing 'criteria_box' for criteria '{criteria}' in document '{document_name}'")
                            all_criteria_sets_met = False
                            break

                        # Define the rectangle for the criteria box
                        criteria_rect = fitz.Rect(
                            criteria_box["x"],
                            criteria_box["y"],
                            criteria_box["x"] + criteria_box["width"],
                            criteria_box["y"] + criteria_box["height"]
                        )

                        # Extract text within the criteria box
                        criteria_clip_text = page.get_text("text", clip=criteria_rect)
                        #print(f"File: {os.path.basename(pdf_path)}:\t|\tCriteria: {criteria}\t|\tClippedText: {criteria_clip_text}")
                        # Store the result for this criteria
                        criteria_met = criteria in criteria_clip_text
                        criteria_results[criteria] = criteria_met

                        if not criteria_met:
                            all_criteria_sets_met = False
                            break

                    except Exception as e:
                        logger.error(f"Error processing criteria_set in document '{document_name}', page {page_number + 1}: {e}")
                        all_criteria_sets_met = False
                        break

                # Only process entities if ALL criteria sets were met
                if all_criteria_sets_met:
                    logger.info(f"{os.path.basename(pdf_path)} | {document_name} | All criteria met for document '{document_name}' on page {page_number + 1}")
                    
                    # Create base entity data
                    entity_data = {
                        "Document": document_name,
                        "Page": page_number + 1,
                        "Criteria_Met": ", ".join(criteria_results.keys()),  # List all met criteria
                        "PDF_File": Path(pdf_path).name,
                        "NumPages": len(doc)
                    }

                    # Process entities
                    for entity in document.get("entities", []):
                        try:
                            entity_name = entity.get("name", "Unknown")
                            entity_coords = entity.get("coordinates", None)

                            if not entity_coords or not isinstance(entity_coords, dict):
                                logger.warning(f"Invalid or missing coordinates for entity '{entity_name}' in document '{document_name}'")
                                continue

                            # Define the rectangle for the entity box
                            entity_rect = fitz.Rect(
                                entity_coords["x"],
                                entity_coords["y"],
                                entity_coords["x"] + entity_coords["width"],
                                entity_coords["y"] + entity_coords["height"]
                            )

                            # Extract text within the entity box
                            entity_clip_text = ' '.join(page.get_text("text", clip=entity_rect).split()).strip()

                            # Add the extracted entity information to the entity_data dictionary
                            entity_data[entity_name] = entity_clip_text

                        except Exception as e:
                            logger.error(f"Error processing entity '{entity_name}' in document '{document_name}', page {page_number + 1}: {e}")

                    # Append the entity data only if we processed all entities
                    pdf_data.append(entity_data)
                else:
                    logger.debug(f"Not all criteria met for document '{document_name}' on page {page_number + 1}")
        doc.close()
        return pdf_data
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {e}")
        return []

def process_all_pdfs(pdf_directory, criteria_file):
    pdf_files = [os.path.join(pdf_directory, f) for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    all_data = []
    with ThreadPoolExecutor() as executor:
        # Map PDF files to the worker function
        results = list(executor.map(lambda x: process_pdf(x, criteria_file), pdf_files))
        for result in results:
            all_data.extend(result)

    return all_data

def main():
    try:
        # Directory containing PDF files
        pdf_directory = r"S:\CLA\August 2024 FF\August 2024 FF Files\it2\it3\it4"
        criteria_file = r"C:\Users\aliner\Desktop\JSON\docclass.json"
        output_file = r'S:\CLA\Classification\extracted_entities2.csv'
        

        logger.info("Starting PDF processing...")
        # Process all PDFs
        pdf_files_data = process_all_pdfs(pdf_directory, criteria_file)

        # Create a DataFrame with the extracted data
        df = pd.DataFrame(pdf_files_data)

        df['AccountNumber'] = df['PDF_File'].astype(str).str[:10]
        #Document	Page	Criteria_Met	PDF_File	document
        ignorelist = ['AccountNumber', 'PDF_File', 'Page', 'Document', 'NumPages', 'criteria', 'document']
        columnlist = [column for column in df.columns if column not in ignorelist]
        columnlist.insert(0, 'AccountNumber')
        columnlist.insert(1, 'PDF_File')
        columnlist.insert(2, 'NumPages')
        columnlist.insert(3, 'Page')
        columnlist.insert(4, 'Document')
        
        output_df = df[columnlist]
        output_df['AccountNumber'] = output_df['AccountNumber'].astype(str).str.zfill(10)
        # Save the DataFrame to a CSV file
        output_df.to_csv(output_file, index=False)

        #Document	Page	Criteria_Met	PDF_File	document

        logger.info(f"Entity extraction complete. Processed {len(pdf_files_data)} matches.")
        logger.info(f"Data saved to '{output_file}'.")

        print(df)

    except Exception as e:
        logger.error("Fatal error in main execution", exc_info=True)
        raise

if __name__ == "__main__":
    main()
