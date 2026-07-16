<!-- Used as Attach & Attach Image Control -->
<script setup>
defineProps(["df"]);
</script>

<template>
	<div class="control editable">
		<div class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<button class="btn btn-sm btn-default">{{ __("Attach") }}</button>
		<div v-if="df.description" class="mt-2 description" v-html="df.description"></div>
	</div>
</template>
