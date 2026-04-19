"use strict";
const { Model, Sequelize } = require("sequelize");

module.exports = (sequelize, DataTypes) => {
  class User extends Model {
    /**
     * Helper method for defining associations.
     * This method is not a part of Sequelize lifecycle.
     * The `models/index` file will call this method automatically.
     */
    static associate(models) {
      // A user can have many ingest jobs
      User.hasMany(models.IngestJob, {
        foreignKey: "userId",
        as: "ingestJobs",
      });
    }
  }

  User.init(
    {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.literal("gen_random_uuid()"),
        allowNull: false,
        primaryKey: true,
      },
      username: {
        type: Sequelize.STRING,
        allowNull: false,
        unique: true,
      },email: {
        type: Sequelize.STRING,
        allowNull: false,
        unique: true,
      },
      password_hash: {
        type: Sequelize.STRING,
        allowNull: false,
      },
      api_key: {
        type: Sequelize.STRING,
        allowNull: true,
        unique: true,
      },
      tier: {
        type: Sequelize.ENUM("free", "byok"),
        allowNull: false,
        defaultValue: "free",
      },
      requests_this_month: {
        type: Sequelize.INTEGER,
        allowNull: false,
        defaultValue: 0,
        
      },
      max_requests: {
        type: Sequelize.INTEGER,
        allowNull: false,
        defaultValue: 50,

      },
      custom_llm_provider: {
        type: Sequelize.STRING,
        allowNull: true,
        
      },
      encrypted_custom_key: {
        type: Sequelize.TEXT,
        allowNull: true,
      },
      createdAt: {
        allowNull: false,
        type: Sequelize.DATE,
        field: "createdAt",
      },
      updatedAt: {
        allowNull: false,
        type: Sequelize.DATE,
        field: "updatedAt",
      },
    },
    {
      sequelize,
      tableName: "users",
      modelName: "User",
      
      hooks: {
        beforeCreate: async (user) => {
          user.api_key = `wiki_sk_${gen_random_uuid().replace(/-/g, '')}`;
        },
      },
    }
  );

  return User;
};