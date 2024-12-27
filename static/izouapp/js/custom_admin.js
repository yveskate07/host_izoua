document.addEventListener('DOMContentLoaded', function () {
    // Sélection des éléments par leurs identifiants
    const statusField = document.querySelector('#id_status');
    const nameField = document.querySelector('#id_name');
    const moitie1Field = document.querySelector('#id_moitie_1');
    const moitie2Field = document.querySelector('#id_moitie_2');

    // Vérifiez si les champs existent
    if (!statusField || !nameField || !moitie1Field || !moitie2Field) {
        console.error('Un ou plusieurs champs sont introuvables dans le DOM.');
        return; // Arrêter l'exécution si les champs sont manquants
    }

    function toggleReadonlyFields() {
        if (statusField.value === "Normale") {
            // Activer 'name', désactiver 'moitie_1' et 'moitie_2'
            if (nameField.readOnly === true){
                nameField.removeAttribute('readonly');
            }
            nameField.value = 'Pizza normale';
            moitie1Field.value = 'Néant';
            moitie2Field.value = 'Néant';
            moitie1Field.setAttribute('readonly', 'readonly');
            moitie2Field.setAttribute('readonly', 'readonly');
        } else if (statusField.value === "Spéciale") {
            // Désactiver 'name', activer 'moitie_1' et 'moitie_2'
            nameField.setAttribute('readonly', 'readonly');
            nameField.value = 'Pizza Spéciale';
            moitie1Field.value = 'Moitié 1';
            moitie2Field.value = 'Moitié 2';
            moitie1Field.removeAttribute('readonly');
            moitie2Field.removeAttribute('readonly');
        }
    }

    // Appliquer la logique au chargement initial
    toggleReadonlyFields();

    // Réagir aux changements de statut
    statusField.addEventListener('change', toggleReadonlyFields);
});