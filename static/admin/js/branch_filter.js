// JavaScript to filter branchAccess based on selected company
(function($) {
    $(document).ready(function() {
        // Function to update branch access options based on selected company
        function updateBranchOptions() {
            var companyId = $('#id_companyId').val();
            var branchAccessFrom = $('#id_branchAccess_from');
            var branchAccessTo = $('#id_branchAccess_to');
            
            if (companyId) {
                // Make AJAX request to get branches for selected company
                $.ajax({
                    url: '/admin/authenticator/user/get-branches-for-company/',
                    type: 'GET',
                    data: {
                        'company_id': companyId
                    },
                    success: function(data) {
                        // Clear current options
                        branchAccessFrom.empty();
                        branchAccessTo.empty();
                        
                        // Add new options
                        $.each(data.branches, function(index, branch) {
                            branchAccessFrom.append(
                                '<option value="' + branch.id + '">' + branch.name + '</option>'
                            );
                        });
                        
                        // Show help text
                        var helpText = branchAccessFrom.closest('.field-branchAccess').find('.help');
                        if (data.branches.length > 0) {
                            helpText.text('Available branches for selected company (' + data.branches.length + ' branches)');
                        } else {
                            helpText.text('No branches available for selected company');
                        }
                    },
                    error: function() {
                        // Clear options on error
                        branchAccessFrom.empty();
                        branchAccessTo.empty();
                        
                        var helpText = branchAccessFrom.closest('.field-branchAccess').find('.help');
                        helpText.text('Error loading branches. Please select a company first.');
                    }
                });
            } else {
                // No company selected, clear branch options
                branchAccessFrom.empty();
                branchAccessTo.empty();
                
                var helpText = branchAccessFrom.closest('.field-branchAccess').find('.help');
                helpText.text('Please select a company first to see available branches');
            }
        }
        
        // Bind change event to company select
        $('#id_companyId').on('change', function() {
            updateBranchOptions();
        });
        
        // Initialize on page load if company is already selected
        if ($('#id_companyId').val()) {
            updateBranchOptions();
        }
    });
})(django.jQuery);