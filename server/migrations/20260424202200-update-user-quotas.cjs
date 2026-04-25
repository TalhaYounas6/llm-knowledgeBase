'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  up: async (queryInterface, Sequelize) => {
    
    await queryInterface.removeColumn('users', 'custom_llm_provider');
    await queryInterface.removeColumn('users', 'requests_this_month');
    await queryInterface.removeColumn('users', 'max_requests');

  
    await queryInterface.addColumn('users', 'requests_today', {
      type: Sequelize.INTEGER,
      defaultValue: 0
    });
    await queryInterface.addColumn('users', 'daily_limit', {
      type: Sequelize.INTEGER,
      defaultValue: 5
    });
  },

  down: async (queryInterface, Sequelize) => {
    
  }
};