'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  up: async (queryInterface, Sequelize) => {
    await queryInterface.sequelize.query(
      'ALTER TABLE "ingest_jobs" ALTER COLUMN "markdown_result" TYPE JSONB USING "markdown_result"::jsonb;'
    );
  },

  down: async (queryInterface, Sequelize) => {
    await queryInterface.sequelize.query(
      'ALTER TABLE "ingest_jobs" ALTER COLUMN "markdown_result" TYPE TEXT;'
    );
  }
};