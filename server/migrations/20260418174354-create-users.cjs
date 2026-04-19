'use strict';
/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    // Create ENUM types
    await queryInterface.sequelize.query(`
      CREATE TYPE "enum_users_tier" AS ENUM ('free', 'byok');
    `);

    await queryInterface.createTable('users', {
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
      },
      password_hash: {
        type: Sequelize.STRING,
        allowNull: false,
      },
      api_key: {
        type: Sequelize.STRING,
        allowNull: false,
        unique: true,
      },
      tier: {
        type: Sequelize.ENUM('free', 'byok'),
        allowNull: false,
        defaultValue: 'free',
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
      },
      updatedAt: {
        allowNull: false,
        type: Sequelize.DATE,
      },
    });
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.dropTable('users');
    // Drop the ENUM type
    await queryInterface.sequelize.query(`DROP TYPE IF EXISTS "enum_users_tier";`);
  },
};