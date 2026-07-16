<template>
	<aside class="afb-sidebar-wrap">
		<details class="afb-sidebar-section" open>
			<summary>Saved Forms</summary>
			<FormList />
		</details>
		<details class="afb-sidebar-section" open>
			<summary>Layouts</summary>
			<LayoutLibrary />
		</details>
		<details class="afb-sidebar-section" open>
			<summary>Field Library</summary>
			<FieldLibrary />
		</details>
	</aside>
</template>

<script setup>
import FormList from "./FormList.vue";
import LayoutLibrary from "./LayoutLibrary.vue";
import FieldLibrary from "./FieldLibrary.vue";
</script>
