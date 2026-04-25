"use strict";
const { Model, Sequelize } = require("sequelize");

module.exports = (sequelize, DataTypes) => {
  class IngestJob extends Model {
    /**
     * Helper method for defining associations.
     * This method is not a part of Sequelize lifecycle.
     * The `models/index` file will call this method automatically.
     */
    static associate(models) {
      // An ingest job belongs to a user
      IngestJob.belongsTo(models.User, {
        foreignKey: "userId",
        as: "user",
      });
    }
  }

  IngestJob.init(
    {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.literal("gen_random_uuid()"),
        allowNull: false,
        primaryKey: true,
      },
      userId: {
        type: Sequelize.UUID,
        allowNull: false,
        references: {
          model: "users",
          key: "id",
        },
        field: "userId",
      },
      original_filename: {
        type: Sequelize.STRING,
        allowNull: false,
        
      },
      status: {
        type: Sequelize.ENUM("pending", "processing", "completed", "failed"),
        allowNull: false,
        defaultValue: "pending",
        validate: {
          isIn: [["pending", "processing", "completed", "failed"]],
        },
      },
      markdown_result: { type: Sequelize.TEXT, allowNull: true },
      error_message: {
        type: Sequelize.TEXT,
        allowNull: true,
        field: "error_message",
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
      tableName: "ingest_jobs",
      modelName: "IngestJob",
    }
  );

  return IngestJob;
};