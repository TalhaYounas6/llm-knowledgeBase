'use strict';
/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    // Create ENUM type for status
    await queryInterface.sequelize.query(`
      CREATE TYPE "enum_ingestjobs_status" AS ENUM ('pending', 'processing', 'completed', 'failed');
    `);

    await queryInterface.createTable('ingest_jobs', {
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
          model: 'users',
          key: 'id',
        },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
      },
      original_filename: {
        type: Sequelize.STRING,
        allowNull: false,
      },
      status: {
        type: Sequelize.ENUM('pending', 'processing', 'completed', 'failed'),
        allowNull: false,
        defaultValue: 'pending',
      },
      error_message: {
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
    await queryInterface.dropTable('ingest_jobs');
    // Drop the ENUM type
    await queryInterface.sequelize.query(`DROP TYPE IF EXISTS "enum_ingestjobs_status";`);
  },
};