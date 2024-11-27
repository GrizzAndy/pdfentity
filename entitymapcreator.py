import sys
import fitz  # PyMuPDF
from PyQt6 import QtWidgets, QtGui, QtCore
from PIL import Image
import json

class PDFAnnotationTool(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)  # Increased size for better layout

        # Initialize PDF and Annotation Data
        self.pdf_document = None
        self.current_page_index = 0
        self.documents = []  # Updated data structure
        self.zoom_level = 1.0
        self.start_x = 0
        self.start_y = 0
        self.rect = None
        self.selected_document_index = None
        self.selected_criteria_set_index = None
        self.selected_entity_index = None

        # Undo/Redo Stacks
        self.undo_stack = []
        self.redo_stack = []

        # UI Setup
        self.setup_ui()

    def setup_ui(self):
        # Central Widget
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        # Layouts
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        viewer_layout = QtWidgets.QVBoxLayout()
        sidebar_layout = QtWidgets.QVBoxLayout()

        # Viewer Area
        self.viewer = QtWidgets.QLabel(self)
        self.viewer.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.viewer.setMouseTracking(True)
        self.viewer.mousePressEvent = self.start_draw_rectangle
        self.viewer.mouseMoveEvent = self.update_rectangle
        self.viewer.mouseReleaseEvent = self.finish_rectangle
        self.viewer.wheelEvent = self.handle_wheel_event  # Add mouse wheel event for zoom in and out

        viewer_scroll_area = QtWidgets.QScrollArea()
        viewer_scroll_area.setWidgetResizable(True)
        viewer_scroll_area.setWidget(self.viewer)
        viewer_scroll_area.setStyleSheet("border: 2px solid #ccc; background-color: white;")
        viewer_layout.addWidget(viewer_scroll_area)

        # Toolbar
        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(16, 16))
        self.addToolBar(toolbar)

        # File actions with icons
        open_action = QtGui.QAction(QtGui.QIcon('icons/open.png'), "Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        new_json_action = QtGui.QAction(QtGui.QIcon('icons/new.png'), "New JSON", self)
        new_json_action.triggered.connect(self.new_json)
        toolbar.addAction(new_json_action)

        save_json_action = QtGui.QAction(QtGui.QIcon('icons/save.png'), "Save JSON", self)
        save_json_action.triggered.connect(self.save_json)
        toolbar.addAction(save_json_action)

        load_json_action = QtGui.QAction(QtGui.QIcon('icons/load.png'), "Load JSON", self)
        load_json_action.triggered.connect(self.load_json)
        toolbar.addAction(load_json_action)

        export_annotations_action = QtGui.QAction(QtGui.QIcon('icons/export.png'), "Export Annotations", self)
        export_annotations_action.triggered.connect(self.export_annotations)
        toolbar.addAction(export_annotations_action)

        # Navigation actions
        previous_page_action = QtGui.QAction(QtGui.QIcon('icons/prev.png'), "Previous Page", self)
        previous_page_action.triggered.connect(self.previous_page)
        toolbar.addAction(previous_page_action)

        next_page_action = QtGui.QAction(QtGui.QIcon('icons/next.png'), "Next Page", self)
        next_page_action.triggered.connect(self.next_page)
        toolbar.addAction(next_page_action)

        zoom_in_action = QtGui.QAction(QtGui.QIcon('icons/zoom_in.png'), "Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QtGui.QAction(QtGui.QIcon('icons/zoom_out.png'), "Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        reset_zoom_action = QtGui.QAction(QtGui.QIcon('icons/reset.png'), "Reset Zoom", self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        toolbar.addAction(reset_zoom_action)

        # Sidebar for Document, Criteria, and Entities Management
        sidebar_tabs = QtWidgets.QTabWidget()

        # Document Tab
        document_tab = QtWidgets.QWidget()
        document_layout = QtWidgets.QVBoxLayout(document_tab)
        self.document_list = QtWidgets.QListWidget()
        self.document_list.itemClicked.connect(self.select_document)
        document_layout.addWidget(self.document_list)

        add_document_btn = QtWidgets.QPushButton("Add Document")
        add_document_btn.clicked.connect(self.add_document)
        document_layout.addWidget(add_document_btn)

        delete_document_btn = QtWidgets.QPushButton("Delete Document")
        delete_document_btn.clicked.connect(self.delete_document)
        document_layout.addWidget(delete_document_btn)

        sidebar_tabs.addTab(document_tab, "Documents")

        # Criteria Tab
        criteria_tab = QtWidgets.QWidget()
        criteria_layout = QtWidgets.QVBoxLayout(criteria_tab)
        self.criteria_list = QtWidgets.QListWidget()
        self.criteria_list.itemClicked.connect(self.highlight_criteria)
        criteria_layout.addWidget(self.criteria_list)

        add_criteria_btn = QtWidgets.QPushButton("Add Criteria")
        add_criteria_btn.clicked.connect(self.add_criteria)
        criteria_layout.addWidget(add_criteria_btn)

        delete_criteria_btn = QtWidgets.QPushButton("Delete Criteria")
        delete_criteria_btn.clicked.connect(self.delete_criteria)
        criteria_layout.addWidget(delete_criteria_btn)

        self.criteria_name_input = QtWidgets.QLineEdit()
        self.criteria_name_input.setPlaceholderText("Set Criteria Name")
        self.criteria_name_input.returnPressed.connect(self.set_criteria_name)
        criteria_layout.addWidget(self.criteria_name_input)

        self.criteria_box_input = QtWidgets.QLineEdit()
        self.criteria_box_input.setPlaceholderText("Set Criteria Box (x, y, width, height)")
        self.criteria_box_input.returnPressed.connect(self.set_criteria_box)
        criteria_layout.addWidget(self.criteria_box_input)

        sidebar_tabs.addTab(criteria_tab, "Criteria")

        # Entity Tab
        entity_tab = QtWidgets.QWidget()
        entity_layout = QtWidgets.QVBoxLayout(entity_tab)
        self.entity_list = QtWidgets.QListWidget()
        self.entity_list.itemClicked.connect(self.highlight_entity)
        entity_layout.addWidget(self.entity_list)

        add_entity_btn = QtWidgets.QPushButton("Add Entity")
        add_entity_btn.clicked.connect(self.add_entity)
        entity_layout.addWidget(add_entity_btn)

        remove_entity_btn = QtWidgets.QPushButton("Remove Entity")
        remove_entity_btn.clicked.connect(self.remove_entity)
        entity_layout.addWidget(remove_entity_btn)

        self.entity_name_input = QtWidgets.QLineEdit()
        self.entity_name_input.setPlaceholderText("Set Entity Name")
        self.entity_name_input.returnPressed.connect(self.set_entity_name)
        entity_layout.addWidget(self.entity_name_input)

        self.entity_coordinates_input = QtWidgets.QLineEdit()
        self.entity_coordinates_input.setPlaceholderText("Set Entity Coordinates (x, y, width, height)")
        self.entity_coordinates_input.returnPressed.connect(self.set_entity_coordinates)
        entity_layout.addWidget(self.entity_coordinates_input)

        preview_text_btn = QtWidgets.QPushButton("Preview Text")
        preview_text_btn.clicked.connect(self.preview_text)
        entity_layout.addWidget(preview_text_btn)

        sidebar_tabs.addTab(entity_tab, "Entities")

        # Undo/Redo Buttons
        undo_redo_tab = QtWidgets.QWidget()
        undo_redo_layout = QtWidgets.QVBoxLayout(undo_redo_tab)
        undo_btn = QtWidgets.QPushButton("Undo")
        undo_btn.clicked.connect(self.undo_action)
        undo_redo_layout.addWidget(undo_btn)

        redo_btn = QtWidgets.QPushButton("Redo")
        redo_btn.clicked.connect(self.redo_action)
        undo_redo_layout.addWidget(redo_btn)

        sidebar_tabs.addTab(undo_redo_tab, "Undo/Redo")

        sidebar_layout.addWidget(sidebar_tabs)
        sidebar_layout.addStretch()

        # Combine Layouts
        main_layout.addLayout(viewer_layout, 3)  # Occupy more space for viewer
        main_layout.addLayout(sidebar_layout, 1)  # Sidebar takes less space

    def add_document(self):
        document_name, ok = QtWidgets.QInputDialog.getText(self, "Document Name", "Enter document name:")
        if not ok or not document_name.strip():
            document_name = f"Document {len(self.documents) + 1}"
        new_document = {"document_name": document_name, "criteria_sets": [], "entities": []}
        self.documents.append(new_document)
        self.document_list.addItem(new_document["document_name"])
        self.selected_document_index = len(self.documents) - 1
        self.selected_criteria_set_index = None
        self.selected_entity_index = None
        self.show_page()
        self.push_undo_stack()

    def add_criteria(self):
        if self.selected_document_index is None:
            QtWidgets.QMessageBox.warning(self, "No Document Selected", "Please select or add a document first.")
            return

        criteria_name = self.criteria_name_input.text().strip()
        if not criteria_name:
            criteria_name, ok = QtWidgets.QInputDialog.getText(self, "Criteria Name", "Enter criteria name:")
            if not ok or not criteria_name.strip():
                criteria_name = f"Criteria {len(self.documents[self.selected_document_index]['criteria_sets']) + 1}"

        # Generate a default rectangle for the criteria
        new_criteria = {
            "criteria": criteria_name,
            "criteria_box": {
                "x": 100,
                "y": 100,
                "width": 200,
                "height": 100
            }
        }

        # Add the criteria to the selected document
        self.documents[self.selected_document_index]["criteria_sets"].append(new_criteria)
        self.criteria_list.addItem(criteria_name)
        self.criteria_name_input.clear()
        self.selected_criteria_set_index = len(self.documents[self.selected_document_index]["criteria_sets"]) - 1
        self.selected_entity_index = None
        self.show_page()
        self.push_undo_stack()

    def new_json(self):
        self.documents = []
        self.document_list.clear()
        self.criteria_list.clear()
        self.entity_list.clear()
        self.selected_document_index = None
        self.selected_criteria_set_index = None
        self.selected_entity_index = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.show_page()

    def delete_document(self):
        selected_items = self.document_list.selectedItems()
        if selected_items:
            index = self.document_list.row(selected_items[0])
            del self.documents[index]
            self.document_list.takeItem(index)
            self.selected_document_index = None if not self.documents else 0
            self.selected_criteria_set_index = None
            self.selected_entity_index = None
            self.show_page()
            self.push_undo_stack()

    def select_document(self, item):
        self.selected_document_index = self.document_list.row(item)
        self.criteria_list.clear()
        self.entity_list.clear()
        if self.selected_document_index is not None:
            document = self.documents[self.selected_document_index]
            self.document_list.setCurrentRow(self.selected_document_index)  # Ensure document name is properly selected
            for criteria_set in document.get("criteria_sets", []):
                self.criteria_list.addItem(criteria_set.get("criteria", "Unnamed Criteria"))
            for entity in document.get("entities", []):
                self.entity_list.addItem(entity.get("name", "Unnamed Entity"))
        self.selected_criteria_set_index = None
        self.selected_entity_index = None
        self.show_page()

    def open_pdf(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf_document = fitz.open(file_path)
            self.current_page_index = 0
            self.show_page()

    def show_page(self):
        if self.pdf_document is not None:
            # Load the current page
            page = self.pdf_document.load_page(self.current_page_index)

            # Apply zoom transformation
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=mat)

            # Convert the pixmap to a QImage for display
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            q_image = QtGui.QImage(data, img.width, img.height, QtGui.QImage.Format.Format_RGBA8888)

            # Update the viewer with the zoomed PDF page
            pixmap = QtGui.QPixmap.fromImage(q_image)
            self.viewer.setPixmap(pixmap)
            self.viewer.adjustSize()

            # Redraw rectangles for the selected document, criteria set, and its entities
            if self.selected_document_index is not None:
                document = self.documents[self.selected_document_index]
                if self.selected_criteria_set_index is not None:
                    criteria_set = document["criteria_sets"][self.selected_criteria_set_index]
                    self.draw_rectangle(criteria_set["criteria_box"], color=QtCore.Qt.GlobalColor.blue, label=criteria_set.get("criteria", "Unnamed Criteria"))
                for entity in document["entities"]:
                    if "coordinates" in entity:
                        self.draw_rectangle(entity["coordinates"], color=QtCore.Qt.GlobalColor.green, label=entity.get("name", "Unnamed Entity"))

    def save_json(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.json)")
        if file_path:
            # Wrap the documents in the "documents" structure
            output_data = {"documents": self.documents}
            with open(file_path, 'w') as json_file:
                json.dump(output_data, json_file, indent=4)

    def load_json(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load JSON File", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)

            # Check if the JSON has a "documents" key
            if "documents" in data:
                self.documents = data["documents"]
            else:
                self.documents = data

            self.selected_document_index = 0 if self.documents else None
            self.selected_criteria_set_index = None
            self.selected_entity_index = None
            self.document_list.clear()
            for document in self.documents:
                self.document_list.addItem(document.get("document_name", "Unnamed Document"))
            self.show_page()

    def export_annotations(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Annotations", "", "JSON Files (*.json)")
        if file_path:
            # Wrap the documents in the "documents" structure
            output_data = {"documents": self.documents}
            with open(file_path, 'w') as json_file:
                json.dump(output_data, json_file, indent=4)

    def previous_page(self):
        if self.pdf_document is not None and self.current_page_index > 0:
            self.current_page_index -= 1
            self.show_page()

    def next_page(self):
        if self.pdf_document is not None and self.current_page_index < len(self.pdf_document) - 1:
            self.current_page_index += 1
            self.show_page()

    def zoom_in(self):
        self.zoom_level *= 1.2
        self.show_page()

    def zoom_out(self):
        self.zoom_level /= 1.2
        self.show_page()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.show_page()

    def handle_wheel_event(self, event):
        # Handle zoom with Ctrl + scroll
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

    def start_draw_rectangle(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Start editing the selected criteria
            if self.selected_document_index is not None and self.selected_criteria_set_index is not None:
                self.start_x = int(event.position().x() / self.zoom_level)
                self.start_y = int(event.position().y() / self.zoom_level)

                # Initialize the rubber band rectangle for editing
                self.rect = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self.viewer)
                self.rect.setGeometry(QtCore.QRect(
                    int(self.start_x * self.zoom_level),
                    int(self.start_y * self.zoom_level),
                    0, 0
                ))
                self.rect.show()
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            # Start drawing a new rectangle
            self.start_x = int(event.position().x() / self.zoom_level)
            self.start_y = int(event.position().y() / self.zoom_level)

            # Initialize the rubber band rectangle
            self.rect = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self.viewer)
            self.rect.setGeometry(QtCore.QRect(
                int(self.start_x * self.zoom_level),
                int(self.start_y * self.zoom_level),
                0, 0
            ))
            self.rect.show()

    def update_rectangle(self, event):
        if self.rect is not None:
            # Normalize current mouse coordinates to the PDF scale
            current_x = int(event.position().x() / self.zoom_level)
            current_y = int(event.position().y() / self.zoom_level)

            # Update the rubber band geometry
            self.rect.setGeometry(QtCore.QRect(
                int(self.start_x * self.zoom_level),
                int(self.start_y * self.zoom_level),
                int((current_x - self.start_x) * self.zoom_level),
                int((current_y - self.start_y) * self.zoom_level)
            ))

    def finish_rectangle(self, event):
        if self.rect is not None:
            # Normalize ending coordinates to the PDF scale
            end_x = int(event.position().x() / self.zoom_level)
            end_y = int(event.position().y() / self.zoom_level)

            if event.button() == QtCore.Qt.MouseButton.RightButton:
                # Edit the selected criteria with the new dimensions
                if self.selected_document_index is not None and self.selected_criteria_set_index is not None:
                    selected_document = self.documents[self.selected_document_index]
                    criteria_set = selected_document['criteria_sets'][self.selected_criteria_set_index]
                    criteria_set['criteria_box'] = {
                        "x": self.start_x,
                        "y": self.start_y,
                        "width": end_x - self.start_x,
                        "height": end_y - self.start_y
                    }
                    self.show_page()
                    self.push_undo_stack()
            elif event.button() == QtCore.Qt.MouseButton.LeftButton:
                # Add a new entity with the drawn rectangle
                if self.selected_document_index is None or self.selected_criteria_set_index is None:
                    QtWidgets.QMessageBox.warning(self, "No Criteria Selected", "Please select a criteria set first.")
                    self.rect.hide()
                    self.rect = None
                    return

                # Get the selected document and criteria set
                selected_document = self.documents[self.selected_document_index]
                selected_criteria_set = selected_document["criteria_sets"][self.selected_criteria_set_index]

                # Save the rectangle coordinates normalized to the PDF scale
                new_entity = {
                    "name": f"Entity {len(selected_document['entities']) + 1}",
                    "text": "",
                    "coordinates": {
                        "x": self.start_x,
                        "y": self.start_y,
                        "width": end_x - self.start_x,
                        "height": end_y - self.start_y
                    }
                }

                # Add the entity to the selected document
                selected_document['entities'].append(new_entity)

                # Update the UI
                self.entity_list.addItem(new_entity["name"])
                self.update_entity_list(selected_document)
                self.show_page()
                self.push_undo_stack()

            # Reset the rectangle
            self.rect.hide()
            self.rect = None

    def draw_rectangle(self, rect_data, color=QtCore.Qt.GlobalColor.red, label=None):
        pixmap = self.viewer.pixmap()
        if pixmap is None:
            return

        # Apply zoom transformation to rectangle coordinates
        # Use get() with default values to handle missing keys
        scaled_x = rect_data.get("x", 0) * self.zoom_level
        scaled_y = rect_data.get("y", 0) * self.zoom_level
        scaled_width = rect_data.get("width", 0) * self.zoom_level
        scaled_height = rect_data.get("height", 0) * self.zoom_level

        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(int(scaled_x), int(scaled_y), int(scaled_width), int(scaled_height))

        # Optionally draw a label above the rectangle
        if label:
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
            painter.setFont(QtGui.QFont("Arial", 10))
            painter.drawText(int(scaled_x), int(scaled_y - 5), label)

        painter.end()
        self.viewer.setPixmap(pixmap)
        self.viewer.update()

    def add_entity(self):
        # Ensure a document is selected
        if self.selected_document_index is None:
            QtWidgets.QMessageBox.warning(self, "No Document Selected", "Please select a document to add an entity.")
            return

        # Get the entity name from the input
        entity_name = self.entity_name_input.text().strip()
        if not entity_name:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Entity name cannot be empty.")
            return

        expected_text = self.entity_text_input.text().strip()
        if not expected_text:
            expected_text = ""

        # Generate default coordinates for the entity
        new_entity = {
            "name": entity_name,
            "text": expected_text,
            "coordinates": {
                "x": 150,  # Default coordinates
                "y": 150,
                "width": 100,
                "height": 100
            }
        }

        # Append the new entity to the selected document
        selected_document = self.documents[self.selected_document_index]
        selected_document['entities'].append(new_entity)

        # Update the UI
        self.entity_list.addItem(entity_name)
        self.entity_name_input.clear()
        self.entity_text_input.clear()
        self.update_entity_list(selected_document)
        self.show_page()
        self.push_undo_stack()  # Save the state for undo

    def set_entity_text(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items:
            index = self.entity_list.row(selected_items[0])
            self.documents[self.selected_document_index]['entities'][index]['text'] = self.entity_text_input.text()
            self.entity_list.item(index).setText(self.entity_name_input.text())
            self.entity_text_input.clear()
            self.show_page()
            self.push_undo_stack()

    def remove_entity(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items:
            entity_index = self.entity_list.row(selected_items[0])
            if self.selected_document_index is not None:
                selected_document = self.documents[self.selected_document_index]
                del selected_document['entities'][entity_index]
                self.update_entity_list(selected_document)
                self.show_page()
                self.push_undo_stack()

    def delete_criteria(self):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            for item in selected_items:
                index = self.criteria_list.row(item)
                if self.selected_document_index is not None:
                    del self.documents[self.selected_document_index]['criteria_sets'][index]
                    self.criteria_list.takeItem(index)
            self.selected_criteria_set_index = None
            self.update_entity_list()
            self.show_page()  # Update to remove deleted rectangles
            self.push_undo_stack()

    def set_criteria_box(self):
        if self.selected_document_index is not None and self.selected_criteria_set_index is not None:
            criteria_box_values = self.criteria_box_input.text().split(',')
            if len(criteria_box_values) == 4:
                try:
                    x, y, width, height = map(int, criteria_box_values)
                    selected_document = self.documents[self.selected_document_index]
                    criteria_set = selected_document['criteria_sets'][self.selected_criteria_set_index]
                    criteria_set['criteria_box'] = {
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height
                    }
                    self.criteria_box_input.clear()
                    self.show_page()
                    self.push_undo_stack()
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid integer values for coordinates.")

    def set_entity_coordinates(self):
        if self.selected_document_index is not None and self.selected_entity_index is not None:
            entity_coords_values = self.entity_coordinates_input.text().split(',')
            if len(entity_coords_values) == 4:
                try:
                    x, y, width, height = map(int, entity_coords_values)
                    selected_document = self.documents[self.selected_document_index]
                    entity = selected_document['entities'][self.selected_entity_index]
                    entity['coordinates'] = {
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": height
                    }
                    self.entity_coordinates_input.clear()
                    self.show_page()
                    self.push_undo_stack()
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid integer values for coordinates.")

    def highlight_criteria(self, item):
        # Get the selected criteria index
        index = self.criteria_list.row(item)
        self.selected_criteria_set_index = index

        # Refresh the viewer
        self.show_page()

        # Get the selected document and criteria set
        if self.selected_document_index is not None:
            document = self.documents[self.selected_document_index]
            criteria_set = document["criteria_sets"][index]

            # Draw the rectangle for the criteria using default values if necessary
            self.draw_rectangle(criteria_set.get("criteria_box", {}), color=QtCore.Qt.GlobalColor.blue, label=criteria_set.get("criteria", "Unnamed Criteria"))

            # Update the entity list to reflect the selected criteria
            self.update_entity_list(document)

    def highlight_entity(self, item):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            # Get the selected entity
            entity_index = self.entity_list.row(item)
            self.selected_entity_index = entity_index
            self.show_page()

    def update_entity_list(self, document=None):
        self.entity_list.clear()
        if document:
            for entity in document['entities']:
                self.entity_list.addItem(entity.get('name', 'Unnamed Entity'))

    def set_criteria_name(self):
        selected_items = self.criteria_list.selectedItems()
        if selected_items:
            index = self.criteria_list.row(selected_items[0])
            self.documents[self.selected_document_index]['criteria_sets'][index]['criteria'] = self.criteria_name_input.text()
            self.criteria_list.item(index).setText(self.criteria_name_input.text())
            self.criteria_name_input.clear()
            self.show_page()
            self.push_undo_stack()

    def set_entity_name(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items:
            index = self.entity_list.row(selected_items[0])
            self.documents[self.selected_document_index]['entities'][index]['name'] = self.entity_name_input.text()
            self.entity_list.item(index).setText(self.entity_name_input.text())
            self.entity_name_input.clear()
            self.show_page()
            self.push_undo_stack()

    def preview_text(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items and self.pdf_document:
            entity_index = self.entity_list.row(selected_items[0])
            entity = self.documents[self.selected_document_index]['entities'][entity_index]

            # Get the current page
            page = self.pdf_document.load_page(self.current_page_index)

            # Extract text within the rectangle (using 300 DPI)
            x = entity['coordinates']['x']
            y = entity['coordinates']['y']
            width = entity['coordinates']['width']
            height = entity['coordinates']['height']
            rect = fitz.Rect(x, y, x + width, y + height)

            # Extract text from the defined area
            extracted_text = page.get_text("text", clip=rect)

            # Show the extracted text in a message box
            expected_text = entity.get('text', '')
            message = f"Extracted Text: {extracted_text if extracted_text else 'No text found in the selected area.'}"
            if expected_text:
                message += f"\nExpected Text: {expected_text}"
            QtWidgets.QMessageBox.information(self, "Extracted Text", message)

    def push_undo_stack(self):
        # Make a deep copy of annotations to push to the undo stack
        self.undo_stack.append(json.loads(json.dumps(self.documents)))
        self.redo_stack.clear()  # Clear the redo stack after a new action

    def undo_action(self):
        if self.undo_stack:
            self.redo_stack.append(json.loads(json.dumps(self.documents)))  # Save current state to redo stack
            self.documents = self.undo_stack.pop()  # Restore the last saved state
            self.refresh_ui()

    def redo_action(self):
        if self.redo_stack:
            self.undo_stack.append(json.loads(json.dumps(self.documents)))  # Save current state to undo stack
            self.documents = self.redo_stack.pop()  # Restore the state
            self.refresh_ui()

    def refresh_ui(self):
        # Update UI elements with the new state of annotations
        self.criteria_list.clear()
        if self.selected_document_index is not None:
            document = self.documents[self.selected_document_index]
            for criteria_set in document.get("criteria_sets", []):
                self.criteria_list.addItem(criteria_set['criteria'])
            if self.selected_criteria_set_index is not None and self.selected_criteria_set_index < len(document["criteria_sets"]):
                self.criteria_list.setCurrentRow(self.selected_criteria_set_index)
            self.update_entity_list(document)
        self.show_page()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = PDFAnnotationTool()
    window.show()
    sys.exit(app.exec())
