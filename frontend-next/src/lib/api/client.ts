import createClient from 'openapi-fetch';
import type { components, paths } from '#lib/api/schema.js';

// Relative URLs: the dev server proxies /api to the backend, so the site and the API share one origin.
export const api = createClient<paths>();

export type Job = components['schemas']['ImportJobOut'];
export type Count = components['schemas']['CountOut'];
export type RequestRow = components['schemas']['ImportRequestOut'];
export type Monitor = components['schemas']['MonitorOut'];
export type ImportKind = components['schemas']['ImportKind'];
export type ImportCreate = components['schemas']['ImportCreate'];
export type NestingNode = components['schemas']['NestingNode'];

export type Me = components['schemas']['MeOut'];
export type AlbumPatch = components['schemas']['AlbumPatch'];
export type ArtistPatch = components['schemas']['ArtistPatch'];
export type SongPatch = components['schemas']['SongPatch'];
export type NicknameOut = components['schemas']['NicknameOut'];
export type NicknameIn = components['schemas']['NicknameIn'];
export type NicknameScope = components['schemas']['NicknameScope'];
export type ReleaseRef = components['schemas']['ReleaseRef'];
export type MemberOut = components['schemas']['MemberOut'];
export type MemberIn = components['schemas']['MemberIn'];
export type SongCard = components['schemas']['SongCard'];
export type PreviewMember = components['schemas']['PreviewMember'];
export type Group = components['schemas']['Group'];
export type ArtistHit = components['schemas']['ArtistSearchHit'];

export type ArtistCard = components['schemas']['ArtistCard'];
export type RoleCount = components['schemas']['RoleCount'];
export type WorkRoleCount = components['schemas']['WorkRoleCount'];

export type ArtistDetail = components['schemas']['ArtistDetail'];
export type ArtistRef = components['schemas']['ArtistRef'];
export type ArtistSong = components['schemas']['ArtistSong'];
export type ArtistAlbum = components['schemas']['ArtistAlbum'];
export type SeriesOut = components['schemas']['SeriesOut'];
export type SeriesIn = components['schemas']['SeriesIn'];

export type AlbumDetail = components['schemas']['AlbumDetail'];
export type AlbumNeighbors = components['schemas']['AlbumNeighbors'];
export type AlbumTrack = components['schemas']['AlbumTrackOut'];
export type AlbumVideo = components['schemas']['AlbumVideoOut'];
export type CreditGroup = components['schemas']['CreditGroup'];
export type RelatedAlbums = components['schemas']['RelatedAlbums'];
export type ArtistVideo = components['schemas']['ArtistVideo'];

export type SongDetail = components['schemas']['SongDetail'];
export type RelatedSongs = components['schemas']['RelatedSongs'];
export type Lyrics = components['schemas']['LyricsOut'];
