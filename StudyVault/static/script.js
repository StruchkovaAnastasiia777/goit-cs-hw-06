// StudyVault

// управління файлами для учебных материалов
class StudyVaultStorage {
  constructor() {
    this.storageKey = "studyvault_files";
    this.indexKey = "studyvault_index";
  }

  // отримання всіх файлів
  getAllFiles() {
    const stored = localStorage.getItem(this.storageKey);
    return stored ? JSON.parse(stored) : [];
  }

  // Збереження файлу
  saveFile(fileData) {
    const files = this.getAllFiles();
    const existingIndex = files.findIndex(
      (f) => f.filename === fileData.filename
    );

    if (existingIndex >= 0) {
      files[existingIndex] = fileData;
    } else {
      files.push(fileData);
    }

    localStorage.setItem(this.storageKey, JSON.stringify(files));
    this.updateSearchIndex();
    console.log("✅ Файл сохранен:", fileData.filename);
  }

  // Видалення файлу
  deleteFile(filename) {
    const files = this.getAllFiles();
    const filtered = files.filter((f) => f.filename !== filename);
    localStorage.setItem(this.storageKey, JSON.stringify(filtered));
    this.updateSearchIndex();
    console.log("🗑️ Файл удален:", filename);
  }

  // Створення пошукового індексу
  updateSearchIndex() {
    const files = this.getAllFiles();
    const index = {};

    files.forEach((file) => {
      const words = this.extractWords(file.content + " " + file.filename);
      words.forEach((word) => {
        if (!index[word]) {
          index[word] = [];
        }
        if (!index[word].includes(file.filename)) {
          index[word].push(file.filename);
        }
      });
    });

    localStorage.setItem(this.indexKey, JSON.stringify(index));
    console.log("🔍 Поисковый индекс обновлен");
  }

  // Видалення пошукового індексу
  extractWords(text) {
    return text
      .toLowerCase()
      .replace(/[^\w\sа-яё]/g, " ")
      .split(/\s+/)
      .filter((word) => word.length > 2);
  }

  // Пошук файлів
  searchFiles(query) {
    if (!query.trim()) return [];

    const index = JSON.parse(localStorage.getItem(this.indexKey) || "{}");
    const files = this.getAllFiles();
    const searchWords = this.extractWords(query);
    const results = new Map();

    searchWords.forEach((word) => {
      if (index[word]) {
        index[word].forEach((filename) => {
          const file = files.find((f) => f.filename === filename);
          if (file) {
            const score = (results.get(filename) || 0) + 1;
            results.set(filename, score);
          }
        });
      }
    });

    // Сортуємо результати за кількістю збігів
    return Array.from(results.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([filename]) => files.find((f) => f.filename === filename))
      .slice(0, 10);
  }
}

//  Глобальні змінні
const storage = new StudyVaultStorage();

// Завантаження файлу
async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const categorySelect = document.getElementById("categorySelect");

  if (!fileInput.files || fileInput.files.length === 0) {
    alert("❌ Виберіть файл для завантаження!");
    return;
  }

  const files = Array.from(fileInput.files);
  let successCount = 0;

  for (const file of files) {
    try {
      console.log("📁 Обробляємо файл:", file.name);

      const content = await readFileContent(file);
      const fileData = {
        filename: file.name,
        content: content,
        size: file.size,
        category: categorySelect.value,
        modified: new Date().toISOString(),
        type: file.type || "text/plain",
      };

      storage.saveFile(fileData);
      successCount++;
    } catch (error) {
      console.error("❌ Помилка при завантаженні файлу:", file.name, error);
      alert(
        `❌ Помилка при завантаженні файлу "${file.name}": ${error.message}`
      );
    }
  }

  if (successCount > 0) {
    alert(`✅ Успішно завантажено файлів: ${successCount}`);
    fileInput.value = "";
    loadFilesList();
  }
}

// Читання вмісту файлу
function readFileContent(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = function (e) {
      resolve(e.target.result);
    };

    reader.onerror = function () {
      reject(new Error("Не вдалося прочитати файл"));
    };

    reader.readAsText(file, "UTF-8");
  });
}

//  Показати модальне вікно з інформацією про файл
function performSearch() {
  const searchInput = document.getElementById("searchInput");
  const query = searchInput.value.trim();

  if (!query) {
    document.getElementById("searchResults").innerHTML =
      '<p style="text-align: center; color: #666;">📝 Введите запрос для поиска</p>';
    return;
  }

  console.log("🔍 Пошук:", query);

  const results = storage.searchFiles(query);
  displaySearchResults(results, query);
}

//  Відображення результатів пошуку
function displaySearchResults(results, query) {
  const container = document.getElementById("searchResults");

  if (results.length === 0) {
    container.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #666;">
                <h3>😔 Нічого не знайдено</h3>
                <p>По запиту "${query}" результатів немає</p>
            </div>
        `;
    return;
  }

  let html = `<h3 style="color: #48bb78; margin-bottom: 1rem;">
        🎯 Знайдено результатів: ${results.length}
    </h3>`;

  results.forEach((file) => {
    const snippet = createSearchSnippet(file.content, query);
    const categoryEmoji = getCategoryEmoji(file.category);

    html += `
            <div class="search-result" onclick="showFileModal(${JSON.stringify(
              file
            ).replace(/"/g, "&quot;")})">
                <div class="search-result-title">
                    ${categoryEmoji} ${file.filename}
                </div>
                <div class="search-result-info">
                    📁 ${file.category} | 📊 ${formatBytes(file.size)} |
                    📅 ${new Date(file.modified).toLocaleDateString()}
                </div>
                <div class="search-result-snippet">
                    ${snippet}
                </div>
            </div>
        `;
  });

  container.innerHTML = html;
}

// Створення сниппета для пошуку
function createSearchSnippet(content, query) {
  const maxLength = 200;
  const queryWords = query.toLowerCase().split(/\s+/);
  const lowerContent = content.toLowerCase();

  // Знаходимо найкращу позицію для підсвічування
  let bestPosition = 0;
  let bestScore = 0;

  queryWords.forEach((word) => {
    const pos = lowerContent.indexOf(word);
    if (pos !== -1 && pos > bestScore) {
      bestPosition = pos;
      bestScore = pos;
    }
  });

  // Визначаємо початок і кінець сниппета
  const start = Math.max(0, bestPosition - maxLength / 2);
  const end = Math.min(content.length, start + maxLength);

  let snippet = content.substring(start, end);

  // Якщо сниппет занадто короткий, розширюємо його
  if (start > 0) snippet = "..." + snippet;
  if (end < content.length) snippet = snippet + "...";

  // Підсвічуємо збіги
  queryWords.forEach((word) => {
    if (word.length > 2) {
      const regex = new RegExp(`(${escapeRegex(word)})`, "gi");
      snippet = snippet.replace(regex, "<mark>$1</mark>");
    }
  });

  return snippet;
}

// Екранірування регулярних виразів
function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

//  Показати модальне вікно з інформацією про файл
function loadFilesList() {
  const files = storage.getAllFiles();
  const container = document.getElementById("filesList");

  if (files.length === 0) {
    container.innerHTML = `
            <div style="text-align: center; color: #666; padding: 2rem;">
                <h3>📂 Файлів поки немає</h3>
                <p>Завантажте перший файл, щоб почати!</p>
            </div>
        `;
    return;
  }

  // Групування по категоріях
  const grouped = files.reduce((acc, file) => {
    if (!acc[file.category]) {
      acc[file.category] = [];
    }
    acc[file.category].push(file);
    return acc;
  }, {});

  let html = "";

  Object.entries(grouped).forEach(([category, categoryFiles]) => {
    const categoryEmoji = getCategoryEmoji(category);

    html += `
            <div style="margin-bottom: 2rem;">
                <h3 style="color: #667eea; margin-bottom: 1rem; border-left: 4px solid #667eea; padding-left: 1rem;">
                    ${categoryEmoji} ${category.toUpperCase()} (${
      categoryFiles.length
    })
                </h3>
                <div class="category-files">
        `;

    categoryFiles.forEach((file) => {
      const preview =
        file.content.length > 100
          ? file.content.substring(0, 100) + "..."
          : file.content;

      html += `
                <div class="file-item" onclick="showFileModal(${JSON.stringify(
                  file
                ).replace(/"/g, "&quot;")})">
                    <div class="file-name">${categoryEmoji} ${
        file.filename
      }</div>
                    <div class="file-info">
                        <span>📊 ${formatBytes(file.size)}</span>
                        <span>📅 ${new Date(
                          file.modified
                        ).toLocaleDateString()}</span>
                    </div>
                    <div class="file-preview">${escapeHtml(preview)}</div>
                </div>
            `;
    });

    html += "</div></div>";
  });

  container.innerHTML = html;

  updateLibraryCounters();
}

//  Оновлення лічильників бібліотеки
function updateLibraryCounters() {
  const files = storage.getAllFiles();
  const categories = {
    конспекти: 0,
    шпаргалки: 0,
    код: 0,
    терміни: 0,
    всього: files.length,
  };

  files.forEach((file) => {
    const category = file.category.toLowerCase();
    if (categories.hasOwnProperty(category)) {
      categories[category]++;
    }
    if (category === "примери-кода") {
      categories["код"]++;
    }
  });

  // Оновлення DOM елементів, якщо вони існують
  Object.entries(categories).forEach(([key, count]) => {
    const elements = document.querySelectorAll(
      `[data-category="${key}"] .count`
    );
    elements.forEach((el) => {
      el.textContent = count;
    });
  });
}

//  Показати модальне вікно з інформацією про файл
function getCategoryEmoji(category) {
  const emojis = {
    конспекти: "📋",
    шпаргалки: "🗒️",
    "примери-кода": "💻",
    код: "💻",
    терміни: "📖",
    загальні: "📄",
  };
  return emojis[category] || "📄";
}

//  Форматування розміру файлу
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return "0 байт";

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["байт", "КБ", "МБ", "ГБ"];

  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

//  Екранування HTML
function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

// Показати модальне вікно з інформацією про файл
function downloadFileContent(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  console.log("Файл завантажено:", filename);
}

// Обробники подій
document.addEventListener("DOMContentLoaded", function () {
  console.log("🚀 StudyVault іниціалізовано");

  // Завантаження списку файлів
  loadFilesList();

  // Пошук по Enter
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        performSearch();
      }
    });

    // Живий пошук (опціонально)
    searchInput.addEventListener("input", function () {
      if (this.value.length > 2) {
        performSearch();
      } else if (this.value.length === 0) {
        document.getElementById("searchResults").innerHTML = "";
      }
    });
  }

  // Drag & Drop для завантаження файлів
  const uploadArea = document.querySelector(".upload-form");
  if (uploadArea) {
    uploadArea.addEventListener("dragover", function (e) {
      e.preventDefault();
      this.style.background = "rgba(159, 122, 234, 0.1)";
    });

    uploadArea.addEventListener("dragleave", function (e) {
      e.preventDefault();
      this.style.background = "";
    });

    uploadArea.addEventListener("drop", function (e) {
      e.preventDefault();
      this.style.background = "";

      const fileInput = document.getElementById("fileInput");
      if (fileInput && e.dataTransfer.files) {
        fileInput.files = e.dataTransfer.files;
        uploadFile();
      }
    });
  }
});

// Показати модальне вікно з інформацією про файл
function clearAllData() {
  if (confirm("❌ Видалити ВСІ файли? Це дію не можна скасувати!")) {
    localStorage.removeItem("studyvault_files");
    localStorage.removeItem("studyvault_index");
    loadFilesList();
    document.getElementById("searchResults").innerHTML = "";
    alert("✅ Всі дані очищено");
  }
}

// Показати статистику
function showStats() {
  const files = storage.getAllFiles();
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const categories = {};

  files.forEach((file) => {
    categories[file.category] = (categories[file.category] || 0) + 1;
  });

  console.log("Статистика StudyVault:");
  console.log("Всього файлів:", files.length);
  console.log("Загальний розмір:", formatBytes(totalSize));
  console.log("По категоріях:", categories);
  console.log(
    "Розмір в localStorage:",
    formatBytes(JSON.stringify(files).length)
  );
}
