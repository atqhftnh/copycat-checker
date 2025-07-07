document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById("upload-area");
    const fileInput = document.getElementById("fileInput");
    const browseLink = document.getElementById("browseLink");
    const fileList = document.getElementById("fileList");
    const submitBtn = document.getElementById("submit-btn");
    const roleSelect = document.querySelector('select[name="role"]');
    const studentIdGroup = document.getElementById('studentIdGroup');

    if (uploadArea && fileInput && browseLink && fileList) {
        uploadArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = "#00A0AA";
            uploadArea.style.backgroundColor = "#f0f8ff";
        });

        uploadArea.addEventListener("dragleave", () => {
            uploadArea.style.borderColor = "#ccc";
            uploadArea.style.backgroundColor = "";
        });

        uploadArea.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = "#ccc";
            uploadArea.style.backgroundColor = "";
            handleFiles(e.dataTransfer.files);
        });

        browseLink.addEventListener("click", (e) => {
            e.preventDefault();
            fileInput.click();
        });

        fileInput.addEventListener("change", () => {
            handleFiles(fileInput.files);
        });

        // Handle files function clears display before rendering
        function handleFiles(files) {
            if (files.length === 0) {
                fileList.innerHTML = ""; // Clear display if no files
                return;
            }

            const file = files[0];
            const allowedTypes = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ];

            if (!allowedTypes.includes(file.type)) {
                fileList.innerHTML = `<p class="error-message">Only PDF or DOCX files are allowed.</p>`;
                fileInput.value = "";
                return;
            }

            fileList.innerHTML = `  <!-- Clear and render file info -->
                <div class="file-info">
                    <p><strong>Selected file:</strong> ${file.name}</p>
                    <div class="file-actions">
                        <button id="removeFileBtn" class="btn btn-danger btn-sm">Delete</button>
                        <button id="editFileBtn" class="btn btn-secondary btn-sm">Edit</button>
                    </div>
                </div>
            `;

            if (file.size) {
                const fileSize = (file.size / (1024*1024)).toFixed(2);
                fileList.querySelector('.file-info p').innerHTML += 
                    `<br><span class="file-size">Size: ${fileSize} MB</span>`;
            }

            document.getElementById('removeFileBtn').addEventListener('click', (e) => {
                e.preventDefault();
                fileList.innerHTML = "";
                fileInput.value = "";
            });

            document.getElementById('editFileBtn').addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('editFileModal').style.display = 'block';
                document.getElementById('editFileName').value = file.name;
            });
        }

        // Move this listener *outside* handleFiles to avoid multiple bindings
        document.getElementById('editFileForm').addEventListener('submit', function(e) {
            e.preventDefault();

            const newName = document.getElementById('editFileName').value;
            const newFileInput = document.getElementById('editFileInput');

            if (newFileInput.files.length > 0) {
                const newFile = new File([newFileInput.files[0]], newName, { type: newFileInput.files[0].type });
                fileInput.files = createFileList(newFile);
            } else {
                const currentFile = fileInput.files[0];
                const renamedFile = new File([currentFile], newName, { type: currentFile.type });
                fileInput.files = createFileList(renamedFile);
            }

            document.getElementById('editFileModal').style.display = 'none';

            // Re-render the updated file info cleanly
            handleFiles(fileInput.files);
        });

        function createFileList(file) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            return dataTransfer.files;
        }
    }

    // Other unrelated code below remains unchanged
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            console.log('Navigating to classroom:', this.getAttribute('href'));
        });
    });

    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
          if (this.value === 'student') {
            studentIdGroup.classList.remove('hidden');
            studentIdGroup.querySelector('input').required = true;
          } else {
            studentIdGroup.classList.add('hidden');
            studentIdGroup.querySelector('input').required = false;
          }
        });
        
        roleSelect.dispatchEvent(new Event('change'));
      }
});
