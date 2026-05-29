'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
   up: async (queryInterface, Sequelize) => {
    await queryInterface.changeColumn('users', 'daily_limit', {
      type: Sequelize.INTEGER,
      defaultValue: 30, 
      allowNull: false, 
    });
  },

  down: async (queryInterface, Sequelize) => {
    
    await queryInterface.changeColumn('users', 'daily_limit', {
      type: Sequelize.INTEGER,
      defaultValue: 5, 
      
    });
  }
};