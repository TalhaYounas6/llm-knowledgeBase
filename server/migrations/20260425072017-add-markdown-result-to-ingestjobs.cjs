'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  up: async (queryInterface, Sequelize) => {
    // Adds the column to the database
    
    await queryInterface.addColumn('ingest_jobs', 'markdown_result', {
      type: Sequelize.TEXT,
      allowNull: true, // starts as null when the job is 'pending'
    });
  },

  down: async (queryInterface, Sequelize) => {
    await queryInterface.removeColumn('IngestJobs', 'markdown_result');
  }
};