// StudyVault - MongoDB ініціалізація

// Підключення до бази StudyVault
db = db.getSiblingDB('studyvault');

// Створення колекції для повідомлень
db.createCollection('messages');

// Додавання індексів для оптимізації
db.messages.createIndex({ "date": -1 });
db.messages.createIndex({ "username": 1 });

// Додавання тестових даних
db.messages.insertMany([
    {
        "date": "2024-08-14 18:00:00.000000",
        "username": "admin",
        "message": "Ласкаво просимо до StudyVault! 🎉"
    },
    {
        "date": "2024-08-14 18:01:00.000000",
        "username": "system",
        "message": "База даних MongoDB успішно ініціалізована ✅"
    }
]);

print("✅ StudyVault MongoDB ініціалізовано успішно!");
print("📊 Колекції:", db.getCollectionNames());
print("💬 Повідомлень у базі:", db.messages.countDocuments({}));