"use strict";
const { Model, Sequelize } = require("sequelize");
const crypto = require('crypto');

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
      requests_today: {
            type: DataTypes.INTEGER,
            defaultValue: 0
        },
        daily_limit: {
            type: DataTypes.INTEGER,
            defaultValue: 30 
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
        const rawUuid = crypto.randomUUID().replace(/-/g, '');
        user.api_key = `wiki_sk_${rawUuid}`;
      },
    },
    }
  );

  return User;
};